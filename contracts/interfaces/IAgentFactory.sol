// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IAgentFactory — Layer 8 of the Arc agentic commerce stack
/// @notice One-click agent deployment across the full 7-layer stack.
///   Layer 1: ERC-8004 AgentIdentity   (who the agent is)
///   Layer 2: ERC-8183 AgentJob        (how work gets paid)
///   Layer 3: AgentMarket              (how clients find agents)
///   Layer 4: AgentOrchestrator        (multi-agent revenue splits)
///   Layer 5: AgentRetainer            (recurring subscriptions)
///   Layer 6: AgentStaking             (USDC collateral guarantees)
///   Layer 7: AgentDAO                 (governance + disputes)
///   Layer 8: AgentFactory             (one-click deploy across all layers)
interface IAgentFactory {

    // ─── Deploy Config ───────────────────────────────────────────────────────

    struct DeployConfig {
        // Required: Identity (Layer 1)
        string  name;
        string  metadataURI;
        // Optional: Market Listing (Layer 3)
        bool    listOnMarket;
        uint256 hourlyRateUsdc;       // USDC per hour (6 decimals)
        bytes32[] capabilities;       // keccak256 hashed capability tags
        uint256 availableUntil;       // unix timestamp (0 = indefinite)
        // Optional: Retainer Plan (Layer 5)
        bool    createRetainerPlan;
        uint256 retainerPriceUsdc;    // USDC per interval (6 decimals)
        uint256 retainerInterval;     // seconds between charges
        string  retainerDescription;  // plan description
        // Optional: Staking (Layer 6)
        bool    stakeCollateral;
        uint256 stakeAmountUsdc;      // USDC to lock (6 decimals, requires prior approval)
    }

    // ─── Templates ───────────────────────────────────────────────────────────

    struct AgentTemplate {
        uint256 id;
        string  name;
        string  description;
        string  defaultMetadataURI;
        // Market defaults
        uint256 suggestedHourlyRate;
        bytes32[] defaultCapabilities;
        // Retainer defaults
        uint256 suggestedRetainerPrice;
        uint256 suggestedRetainerInterval;
        // Staking defaults
        uint256 suggestedStakeAmount;
        // Meta
        bool    active;
        address creator;
        uint256 createdAt;
        uint256 useCount;
    }

    // ─── Deployed Agent Record ───────────────────────────────────────────────

    struct DeployedAgent {
        uint256 agentTokenId;
        address owner;
        uint256 templateId;           // 0 = custom (no template)
        bool    listedOnMarket;
        uint256 retainerPlanId;       // 0 = none
        bool    hasStake;
        uint256 deployedAt;
    }

    // ─── Events ──────────────────────────────────────────────────────────────

    event AgentDeployed(
        uint256 indexed agentTokenId,
        address indexed owner,
        uint256 indexed templateId,
        string  name
    );

    event TemplateCreated(
        uint256 indexed templateId,
        address indexed creator,
        string  name
    );

    event TemplateUpdated(uint256 indexed templateId);
    event TemplateDeactivated(uint256 indexed templateId);

    // ─── Agent Deployment ────────────────────────────────────────────────────

    /// @notice Deploy a new agent with custom config across all layers in one tx
    /// @dev Caller must approve USDC if stakeCollateral is true
    /// @return agentTokenId The minted ERC-8004 identity token ID
    function deployAgent(DeployConfig calldata config)
        external returns (uint256 agentTokenId);

    /// @notice Deploy an agent from a template with optional overrides
    /// @param templateId The template to use as base config
    /// @param name Agent name (required override)
    /// @param metadataURI Agent metadata URI (empty = use template default)
    /// @param enableMarket Whether to list on market (uses template defaults)
    /// @param enableRetainer Whether to create retainer plan (uses template defaults)
    /// @param enableStaking Whether to stake collateral (uses template defaults, requires USDC approval)
    function deployFromTemplate(
        uint256 templateId,
        string calldata name,
        string calldata metadataURI,
        bool enableMarket,
        bool enableRetainer,
        bool enableStaking
    ) external returns (uint256 agentTokenId);

    // ─── Template Management ─────────────────────────────────────────────────

    struct TemplateConfig {
        string  name;
        string  description;
        string  defaultMetadataURI;
        uint256 suggestedHourlyRate;
        bytes32[] defaultCapabilities;
        uint256 suggestedRetainerPrice;
        uint256 suggestedRetainerInterval;
        uint256 suggestedStakeAmount;
    }

    function createTemplate(TemplateConfig calldata config)
        external returns (uint256 templateId);

    function updateTemplate(uint256 templateId, TemplateConfig calldata config)
        external;

    function deactivateTemplate(uint256 templateId) external;

    // ─── Views ───────────────────────────────────────────────────────────────

    function getTemplate(uint256 templateId) external view returns (AgentTemplate memory);
    function getActiveTemplates() external view returns (uint256[] memory templateIds);
    function getDeployedAgent(uint256 agentTokenId) external view returns (DeployedAgent memory);
    function getAgentsByOwner(address owner) external view returns (uint256[] memory agentTokenIds);
    function getFactoryStats() external view returns (
        uint256 totalAgentsDeployed,
        uint256 totalTemplates,
        uint256 totalActiveTemplates
    );
}
