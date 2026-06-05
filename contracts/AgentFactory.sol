// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./interfaces/IAgentFactory.sol";

// ─── Minimal interfaces for cross-layer calls ─────────────────────────────

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @dev Layer 1 — ERC-8004 AgentIdentity (V2 with transfer support)
interface IAgentIdentity {
    struct AgentIdentity {
        address owner;
        string  name;
        string  metadataURI;
        uint256 reputation;
        uint256 registeredAt;
        bool    active;
    }
    function registerAgent(string calldata name, string calldata metadataURI) external returns (uint256 tokenId);
    function getAgent(uint256 tokenId) external view returns (AgentIdentity memory);
    function transferAgent(uint256 tokenId, address newOwner) external;
}

/// @dev Layer 3 — AgentMarket
interface IAgentMarket {
    struct AgentListing {
        uint256 agentTokenId;
        address owner;
        uint256 hourlyRateUsdc;
        bytes32[] capabilities;
        uint256 availableUntil;
        bool    active;
    }
    function listAgent(
        uint256 agentTokenId,
        uint256 hourlyRateUsdc,
        bytes32[] calldata capabilities,
        uint256 availableUntil
    ) external;
    function getListing(uint256 agentTokenId) external view returns (AgentListing memory);
}

/// @dev Layer 5 — AgentRetainer
interface IAgentRetainer {
    function createPlan(
        uint256 agentTokenId,
        uint256 priceUsdc,
        uint256 intervalSeconds,
        string calldata description
    ) external returns (uint256 planId);
}

/// @dev Layer 6 — AgentStaking
interface IAgentStaking {
    struct Stake {
        uint256 agentTokenId;
        uint256 amount;
        uint256 stakedAt;
        uint256 slashCount;
        bool    active;
    }
    function stake(uint256 agentTokenId, uint256 amount) external;
    function getStake(uint256 agentTokenId) external view returns (Stake memory);
}

// ──────────────────────────────────────────────────────────────────────────────

/// @title AgentFactory — Layer 8 of the Arc agentic commerce stack
/// @notice One-click agent deployment across the full 7-layer agentic commerce stack.
///         Registers ERC-8004 identity, optionally lists on market, creates retainer
///         plans, stakes USDC collateral — all in a single transaction.
///         Includes a template registry for common agent archetypes.
/// @author sethoshi.eth
contract AgentFactory is IAgentFactory {

    // ─── State ────────────────────────────────────────────────────────────────

    address public owner;

    // Layer contract references
    IAgentIdentity public immutable identity;       // Layer 1
    IAgentMarket   public immutable market;          // Layer 3
    IAgentRetainer  public immutable retainer;       // Layer 5
    IAgentStaking   public immutable staking;        // Layer 6
    IERC20          public immutable usdc;

    // Template registry
    uint256 private _nextTemplateId = 1;
    mapping(uint256 => AgentTemplate) private _templates;
    uint256[] private _activeTemplateIds;
    mapping(uint256 => uint256) private _templateIndexInActive; // templateId → index

    // Deployed agent tracking
    mapping(uint256 => DeployedAgent) private _deployedAgents;  // agentTokenId → record
    mapping(address => uint256[]) private _ownerAgents;         // owner → agentTokenIds
    uint256 public totalAgentsDeployed;
    uint256 public totalTemplates;

    // ─── Constructor ──────────────────────────────────────────────────────────

    constructor(
        address _identity,
        address _market,
        address _retainer,
        address _staking,
        address _usdc
    ) {
        owner    = msg.sender;
        identity = IAgentIdentity(_identity);
        market   = IAgentMarket(_market);
        retainer = IAgentRetainer(_retainer);
        staking  = IAgentStaking(_staking);
        usdc     = IERC20(_usdc);
    }

    // ─── Modifiers ────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "AgentFactory: not owner");
        _;
    }

    modifier onlyTemplateCreator(uint256 templateId) {
        require(
            _templates[templateId].creator == msg.sender || msg.sender == owner,
            "AgentFactory: not template creator"
        );
        _;
    }

    // ─── Agent Deployment ─────────────────────────────────────────────────────

    /// @notice Deploy a new agent with full custom configuration across layers
    /// @dev If stakeCollateral is true, caller must have approved USDC to this contract
    function deployAgent(DeployConfig calldata config)
        external override returns (uint256 agentTokenId)
    {
        return _deploy(config, 0, msg.sender);
    }

    /// @notice Deploy an agent from a template with optional layer toggles
    function deployFromTemplate(
        uint256 templateId,
        string calldata name,
        string calldata metadataURI,
        bool enableMarket,
        bool enableRetainer,
        bool enableStaking
    ) external override returns (uint256 agentTokenId) {
        AgentTemplate storage tmpl = _templates[templateId];
        require(tmpl.active, "AgentFactory: template not active");

        // Build config from template defaults
        string memory uri;
        if (bytes(metadataURI).length > 0) {
            uri = metadataURI;
        } else {
            uri = tmpl.defaultMetadataURI;
        }

        // We need to copy capabilities to memory for the deploy
        bytes32[] memory caps = tmpl.defaultCapabilities;

        DeployConfig memory config = DeployConfig({
            name:                 name,
            metadataURI:          uri,
            listOnMarket:         enableMarket,
            hourlyRateUsdc:       tmpl.suggestedHourlyRate,
            capabilities:         caps,
            availableUntil:       0, // indefinite
            createRetainerPlan:   enableRetainer,
            retainerPriceUsdc:    tmpl.suggestedRetainerPrice,
            retainerInterval:     tmpl.suggestedRetainerInterval,
            retainerDescription:  tmpl.description, // reuse template description
            stakeCollateral:      enableStaking,
            stakeAmountUsdc:      tmpl.suggestedStakeAmount
        });

        tmpl.useCount++;

        return _deploy(config, templateId, msg.sender);
    }

    // ─── Internal Deploy Logic ────────────────────────────────────────────────

    function _deploy(
        DeployConfig memory config,
        uint256 templateId,
        address deployer
    ) internal returns (uint256 agentTokenId) {
        require(bytes(config.name).length > 0, "AgentFactory: empty name");

        // ── Step 1: Register ERC-8004 identity (factory becomes temporary owner) ──
        agentTokenId = identity.registerAgent(config.name, config.metadataURI);

        // ── Step 2: Optional — List on AgentMarket (Layer 3) ──
        if (config.listOnMarket) {
            require(config.hourlyRateUsdc > 0, "AgentFactory: zero hourly rate");
            market.listAgent(
                agentTokenId,
                config.hourlyRateUsdc,
                config.capabilities,
                config.availableUntil
            );
        }

        // ── Step 3: Optional — Create retainer plan (Layer 5) ──
        uint256 retainerPlanId = 0;
        if (config.createRetainerPlan) {
            require(config.retainerPriceUsdc > 0, "AgentFactory: zero retainer price");
            require(config.retainerInterval > 0, "AgentFactory: zero retainer interval");
            retainerPlanId = retainer.createPlan(
                agentTokenId,
                config.retainerPriceUsdc,
                config.retainerInterval,
                config.retainerDescription
            );
        }

        // ── Step 4: Optional — Stake USDC collateral (Layer 6) ──
        if (config.stakeCollateral) {
            require(config.stakeAmountUsdc > 0, "AgentFactory: zero stake amount");
            // Pull USDC from deployer → factory
            require(
                usdc.transferFrom(deployer, address(this), config.stakeAmountUsdc),
                "AgentFactory: USDC pull failed"
            );
            // Approve staking contract
            require(
                usdc.approve(address(staking), config.stakeAmountUsdc),
                "AgentFactory: USDC approve failed"
            );
            // Stake on behalf of the agent
            staking.stake(agentTokenId, config.stakeAmountUsdc);
        }

        // ── Step 5: Transfer agent ownership to deployer ──
        identity.transferAgent(agentTokenId, deployer);

        // ── Step 6: Record deployment ──
        _deployedAgents[agentTokenId] = DeployedAgent({
            agentTokenId:  agentTokenId,
            owner:         deployer,
            templateId:    templateId,
            listedOnMarket: config.listOnMarket,
            retainerPlanId: retainerPlanId,
            hasStake:      config.stakeCollateral,
            deployedAt:    block.timestamp
        });

        _ownerAgents[deployer].push(agentTokenId);
        totalAgentsDeployed++;

        emit AgentDeployed(agentTokenId, deployer, templateId, config.name);
    }

    // ─── Template Management ──────────────────────────────────────────────────

    /// @notice Create a new agent template
    /// @dev Anyone can create templates; factory owner can also manage all templates
    function createTemplate(TemplateConfig calldata config)
        external override returns (uint256 templateId)
    {
        require(bytes(config.name).length > 0, "AgentFactory: empty template name");

        templateId = _nextTemplateId++;
        _writeTemplate(templateId, config);

        _templates[templateId].active    = true;
        _templates[templateId].creator   = msg.sender;
        _templates[templateId].createdAt = block.timestamp;

        _templateIndexInActive[templateId] = _activeTemplateIds.length;
        _activeTemplateIds.push(templateId);
        totalTemplates++;

        emit TemplateCreated(templateId, msg.sender, config.name);
    }

    /// @notice Update an existing template's configuration
    function updateTemplate(uint256 templateId, TemplateConfig calldata config)
        external override onlyTemplateCreator(templateId)
    {
        AgentTemplate storage tmpl = _templates[templateId];
        require(tmpl.active, "AgentFactory: template not active");

        _writeTemplate(templateId, config);

        emit TemplateUpdated(templateId);
    }

    /// @dev Write template fields from config struct (avoids stack-too-deep)
    function _writeTemplate(uint256 templateId, TemplateConfig calldata config) internal {
        AgentTemplate storage tmpl = _templates[templateId];
        tmpl.id = templateId;
        if (bytes(config.name).length > 0) tmpl.name = config.name;
        if (bytes(config.description).length > 0) tmpl.description = config.description;
        if (bytes(config.defaultMetadataURI).length > 0) tmpl.defaultMetadataURI = config.defaultMetadataURI;
        if (config.suggestedHourlyRate > 0) tmpl.suggestedHourlyRate = config.suggestedHourlyRate;
        if (config.defaultCapabilities.length > 0) tmpl.defaultCapabilities = config.defaultCapabilities;
        if (config.suggestedRetainerPrice > 0) tmpl.suggestedRetainerPrice = config.suggestedRetainerPrice;
        if (config.suggestedRetainerInterval > 0) tmpl.suggestedRetainerInterval = config.suggestedRetainerInterval;
        if (config.suggestedStakeAmount > 0) tmpl.suggestedStakeAmount = config.suggestedStakeAmount;
    }

    /// @notice Deactivate a template (cannot be used for new deployments)
    function deactivateTemplate(uint256 templateId)
        external override onlyTemplateCreator(templateId)
    {
        AgentTemplate storage tmpl = _templates[templateId];
        require(tmpl.active, "AgentFactory: already inactive");
        tmpl.active = false;
        _removeFromActive(templateId);
        emit TemplateDeactivated(templateId);
    }

    // ─── Views ────────────────────────────────────────────────────────────────

    function getTemplate(uint256 templateId)
        external view override returns (AgentTemplate memory)
    {
        require(_templates[templateId].createdAt != 0, "AgentFactory: template not found");
        return _templates[templateId];
    }

    function getActiveTemplates()
        external view override returns (uint256[] memory)
    {
        return _activeTemplateIds;
    }

    function getDeployedAgent(uint256 agentTokenId)
        external view override returns (DeployedAgent memory)
    {
        require(
            _deployedAgents[agentTokenId].deployedAt != 0,
            "AgentFactory: agent not deployed via factory"
        );
        return _deployedAgents[agentTokenId];
    }

    function getAgentsByOwner(address ownerAddr)
        external view override returns (uint256[] memory)
    {
        return _ownerAgents[ownerAddr];
    }

    function getFactoryStats()
        external view override returns (
            uint256 _totalAgentsDeployed,
            uint256 _totalTemplates,
            uint256 _totalActiveTemplates
        )
    {
        return (totalAgentsDeployed, totalTemplates, _activeTemplateIds.length);
    }

    // ─── Cross-Layer Agent Profile (read-only aggregation) ────────────────────

    /// @notice Get a unified view of an agent's status across all layers
    /// @param agentTokenId The ERC-8004 token ID
    /// @return name Agent name from identity registry
    /// @return reputation Current reputation in basis points
    /// @return isListed Whether agent is listed on market
    /// @return hourlyRate Market hourly rate (0 if not listed)
    /// @return stakeAmount USDC staked (0 if none)
    /// @return retainerPlanId Retainer plan ID (0 if none)
    function getAgentProfile(uint256 agentTokenId)
        external view returns (
            string memory name,
            uint256 reputation,
            bool isListed,
            uint256 hourlyRate,
            uint256 stakeAmount,
            uint256 retainerPlanId
        )
    {
        // Layer 1: Identity
        IAgentIdentity.AgentIdentity memory agent = identity.getAgent(agentTokenId);
        name       = agent.name;
        reputation = agent.reputation;

        // Layer 3: Market listing
        try market.getListing(agentTokenId) returns (IAgentMarket.AgentListing memory listing) {
            isListed   = listing.active;
            hourlyRate = listing.hourlyRateUsdc;
        } catch {
            isListed   = false;
            hourlyRate = 0;
        }

        // Layer 6: Staking
        try staking.getStake(agentTokenId) returns (IAgentStaking.Stake memory s) {
            stakeAmount = s.amount;
        } catch {
            stakeAmount = 0;
        }

        // Factory record for retainer
        retainerPlanId = _deployedAgents[agentTokenId].retainerPlanId;
    }

    // ─── Admin ────────────────────────────────────────────────────────────────

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "AgentFactory: zero address");
        owner = newOwner;
    }

    // ─── Internal Helpers ─────────────────────────────────────────────────────

    function _removeFromActive(uint256 templateId) internal {
        uint256 idx  = _templateIndexInActive[templateId];
        uint256 last = _activeTemplateIds[_activeTemplateIds.length - 1];
        _activeTemplateIds[idx]      = last;
        _templateIndexInActive[last] = idx;
        _activeTemplateIds.pop();
        delete _templateIndexInActive[templateId];
    }
}
