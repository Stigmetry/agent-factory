// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IERC8004 — AI Agent Identity Standard
interface IERC8004 {
    struct AgentIdentity {
        address owner;
        string name;
        string metadataURI;
        uint256 reputation;
        uint256 registeredAt;
        bool active;
    }

    event AgentRegistered(uint256 indexed tokenId, address indexed owner, string name);
    event CredentialAdded(uint256 indexed tokenId, bytes32 credentialHash);
    event ReputationUpdated(uint256 indexed tokenId, uint256 oldScore, uint256 newScore);

    function registerAgent(string calldata name, string calldata metadataURI) external returns (uint256 tokenId);
    function getAgent(uint256 tokenId) external view returns (AgentIdentity memory);
    function getAgentsByOwner(address owner) external view returns (uint256[] memory);
    function addCredential(uint256 tokenId, bytes32 credentialHash) external;
    function hasCredential(uint256 tokenId, bytes32 credentialHash) external view returns (bool);
    function updateMetadata(uint256 tokenId, string calldata metadataURI) external;
}

/// @title AgentIdentity V2 — ERC-8004 with transferAgent support
/// @notice Adds transferAgent() for factory-pattern deployments.
///         Otherwise identical to V1.
contract AgentIdentityV2 is IERC8004 {
    uint256 private _nextTokenId = 1;

    mapping(uint256 => AgentIdentity) private _agents;
    mapping(address => uint256[]) private _ownerTokens;
    mapping(uint256 => mapping(bytes32 => bool)) private _credentials;

    mapping(address => bool) public trustedUpdaters;
    address public owner;

    // ─── V2 addition: approved operators (for factory pattern) ────────────
    mapping(uint256 => address) private _tokenApprovals;

    event AgentTransferred(uint256 indexed tokenId, address indexed from, address indexed to);
    event Approval(uint256 indexed tokenId, address indexed approved);

    modifier onlyOwner() {
        require(msg.sender == owner, "AgentIdentity: not owner");
        _;
    }

    modifier onlyAgentOwner(uint256 tokenId) {
        require(_agents[tokenId].owner == msg.sender, "AgentIdentity: not agent owner");
        _;
    }

    modifier onlyAgentOwnerOrApproved(uint256 tokenId) {
        require(
            _agents[tokenId].owner == msg.sender || _tokenApprovals[tokenId] == msg.sender,
            "AgentIdentity: not owner or approved"
        );
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // ─── Admin ──────────────────────────────────────────────────────────────

    function setTrustedUpdater(address updater, bool trusted) external onlyOwner {
        trustedUpdaters[updater] = trusted;
    }

    // ─── IERC8004 ───────────────────────────────────────────────────────────

    function registerAgent(string calldata name, string calldata metadataURI)
        external override returns (uint256 tokenId)
    {
        tokenId = _nextTokenId++;
        _agents[tokenId] = AgentIdentity({
            owner: msg.sender,
            name: name,
            metadataURI: metadataURI,
            reputation: 5000,
            registeredAt: block.timestamp,
            active: true
        });
        _ownerTokens[msg.sender].push(tokenId);
        emit AgentRegistered(tokenId, msg.sender, name);
    }

    function getAgent(uint256 tokenId) external view override returns (AgentIdentity memory) {
        require(_agents[tokenId].registeredAt != 0, "AgentIdentity: not found");
        return _agents[tokenId];
    }

    function getAgentsByOwner(address _ownerAddr) external view override returns (uint256[] memory) {
        return _ownerTokens[_ownerAddr];
    }

    function addCredential(uint256 tokenId, bytes32 credentialHash)
        external override onlyAgentOwner(tokenId)
    {
        _credentials[tokenId][credentialHash] = true;
        emit CredentialAdded(tokenId, credentialHash);
    }

    function hasCredential(uint256 tokenId, bytes32 credentialHash)
        external view override returns (bool)
    {
        return _credentials[tokenId][credentialHash];
    }

    function updateMetadata(uint256 tokenId, string calldata metadataURI)
        external override onlyAgentOwner(tokenId)
    {
        _agents[tokenId].metadataURI = metadataURI;
    }

    // ─── Reputation ─────────────────────────────────────────────────────────

    function adjustReputation(uint256 tokenId, int256 delta) external {
        require(trustedUpdaters[msg.sender], "AgentIdentity: not trusted updater");
        AgentIdentity storage agent = _agents[tokenId];
        uint256 old = agent.reputation;
        int256 newScore = int256(old) + delta;
        if (newScore < 0) newScore = 0;
        if (newScore > 10000) newScore = 10000;
        agent.reputation = uint256(newScore);
        emit ReputationUpdated(tokenId, old, agent.reputation);
    }

    // ─── V2: Transfer + Approval (enables factory pattern) ──────────────────

    /// @notice Approve an address to transfer a specific agent
    function approve(uint256 tokenId, address to) external onlyAgentOwner(tokenId) {
        _tokenApprovals[tokenId] = to;
        emit Approval(tokenId, to);
    }

    /// @notice Transfer agent ownership. Callable by owner or approved address.
    function transferAgent(uint256 tokenId, address newOwner)
        external onlyAgentOwnerOrApproved(tokenId)
    {
        require(newOwner != address(0), "AgentIdentity: zero address");
        address oldOwner = _agents[tokenId].owner;
        _agents[tokenId].owner = newOwner;
        _ownerTokens[newOwner].push(tokenId);
        delete _tokenApprovals[tokenId];
        emit AgentTransferred(tokenId, oldOwner, newOwner);
    }

    /// @notice Get approved address for an agent
    function getApproved(uint256 tokenId) external view returns (address) {
        return _tokenApprovals[tokenId];
    }
}
