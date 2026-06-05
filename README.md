# Arc Agent Factory — Layer 8

One-click agent deployment across the full 7-layer Arc agentic commerce stack.

## What It Does

AgentFactory lets anyone deploy a fully configured AI agent in a single transaction:

1. **Mints ERC-8004 identity** (Layer 1) — registers the agent on-chain with name + metadata
2. **Lists on AgentMarket** (Layer 3) — optional marketplace listing with hourly rate + capabilities
3. **Creates retainer plan** (Layer 5) — optional recurring USDC subscription plan
4. **Stakes USDC collateral** (Layer 6) — optional quality guarantee deposit

Plus a **template registry** for common agent archetypes — one-click deploy a "Freelance Dev", "Content Creator", or "Security Auditor" without configuring each layer manually.

## Deployed Contract

| Contract | Address | Network |
|----------|---------|---------|
| AgentFactory | [`0x3c606d295a18250eaf889f10158315532c6e827f`](https://testnet.arcscan.app/address/0x3c606d295a18250eaf889f10158315532c6e827f) | Arc Testnet (Chain ID 5042002) |

## Connected Layers

| Layer | Contract | Address |
|-------|----------|---------|
| 1 | AgentIdentity (ERC-8004) | `0x5Bef356f89425823FC7eebB3A6ED1A678F3b8233` |
| 2 | AgentJob (ERC-8183) | `0xD698d15F776279c0213444a779941e8E0Cbe5094` |
| 3 | AgentMarket | `0x6BAf93EB026b7BC3db651065302D1934Ad577ec1` |
| 4 | AgentOrchestrator | `0xbA99f039b7892d9F546253444c95EDea822471b0` |
| 5 | AgentRetainer | `0x5C80B95Ac3c2eE748F427aBB15Ad5d3E94fcD8D6` |
| 6 | AgentStaking | `0x0107BD44E269888F12dCc32E9bc03E79Ca7Be770` |
| 7 | AgentDAO | `0x213157853e67BC17F4b69B8F3f5b0fe14C64fCf7` |

## Key Functions

### Agent Deployment

```solidity
// Deploy with full custom config
function deployAgent(DeployConfig calldata config) external returns (uint256 agentTokenId);

// Deploy from a pre-built template
function deployFromTemplate(
    uint256 templateId,
    string calldata name,
    string calldata metadataURI,
    bool enableMarket,
    bool enableRetainer,
    bool enableStaking
) external returns (uint256 agentTokenId);
```

### Template Management

```solidity
// Create a reusable agent template
function createTemplate(TemplateConfig calldata config) external returns (uint256 templateId);

// Update or deactivate templates
function updateTemplate(uint256 templateId, TemplateConfig calldata config) external;
function deactivateTemplate(uint256 templateId) external;
```

### Views

```solidity
// Cross-layer agent profile
function getAgentProfile(uint256 agentTokenId) external view returns (
    string memory name, uint256 reputation, bool isListed,
    uint256 hourlyRate, uint256 stakeAmount, uint256 retainerPlanId
);

// Factory stats
function getFactoryStats() external view returns (
    uint256 totalAgentsDeployed, uint256 totalTemplates, uint256 totalActiveTemplates
);
```

## Architecture

```
User calls deployAgent(config)
    │
    ├── 1. identity.registerAgent(name, metadataURI)  →  ERC-8004 NFT minted
    │
    ├── 2. market.listAgent(tokenId, rate, caps)       →  Listed on marketplace
    │
    ├── 3. retainer.createPlan(tokenId, price, interval, desc)  →  Subscription plan
    │
    ├── 4. usdc.transferFrom → staking.stake(tokenId, amount)  →  Collateral locked
    │
    └── 5. identity.safeTransferFrom(factory → user)   →  Ownership transferred
```

## Stack

- **Contract**: Solidity 0.8.24, deployed via py-solc-x + web3.py
- **SDK**: TypeScript (coming soon)
- **MCP Server**: 8+ tools (coming soon)

## License

MIT
