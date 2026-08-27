# Arc Agent Factory — Layer 8

One-click agent deployment across the full 8-layer Arc agentic commerce stack.

## What It Does

AgentFactory lets anyone deploy a fully configured AI agent in a single transaction:

1. **Mints ERC-8004 identity** (Layer 1) — registers the agent on-chain with name + metadata
2. **Lists on AgentMarket** (Layer 3) — optional marketplace listing with hourly rate + capabilities
3. **Creates retainer plan** (Layer 5) — optional recurring USDC subscription plan
4. **Stakes USDC collateral** (Layer 6) — optional quality guarantee deposit

Plus a **template registry** for common agent archetypes — one-click deploy a "Freelance Dev", "Content Creator", or "Security Auditor" without configuring each layer manually.

## Deployed Contracts (V3 — Full Stack Redeploy)

| Layer | Contract | Address |
|-------|----------|---------|
| 8 | AgentFactory | [`0x1e2e8abfa05b0df0c83af5de3580a79f6c7f6398`](https://testnet.arcscan.app/address/0x1e2e8abfa05b0df0c83af5de3580a79f6c7f6398) |
| 1 | AgentIdentity V2 (ERC-8004) | [`0x0bf50994245ab3297ed95665d62192977930fabb`](https://testnet.arcscan.app/address/0x0bf50994245ab3297ed95665d62192977930fabb) |

All on Arc Testnet (Chain ID 5042002).

## Connected Layers (V3)

| Layer | Contract | Address |
|-------|----------|---------|
| 2 | AgentJob (ERC-8183) | `0x2747fc4601933c7bdfeaddf52808a1c0bedc2323` |
| 3 | AgentMarket | `0x79718fbd092276124d5bfed596e91f861d78a547` |
| 4 | AgentOrchestrator | `0x925a80a447dddb7726a24fabc07fd22b76c4e7c1` |
| 5 | AgentRetainer | `0x9ca8bf8a090a2607d14e6cb0228e02ebd3d3329d` |
| 6 | AgentStaking | `0xbbab7b7ed776e169eb6f0284d97f03cef3c5ecef` |
| 7 | AgentDAO | `0x256658aa7be4e4a066d002f9fecd8e60f8efcbb7` |

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
    ├── 1. identity.registerAgent(name, metadataURI)  →  ERC-8004 minted
    │
    ├── 2. market.listAgent(tokenId, rate, caps)       →  Listed on marketplace
    │
    ├── 3. retainer.createPlan(tokenId, price, interval, desc)  →  Subscription plan
    │
    ├── 4. usdc.transferFrom → staking.stake(tokenId, amount)  →  Collateral locked
    │
    └── 5. identity.transferAgent(factory → user)      →  Ownership transferred
```

## Stack

- **Contract**: Solidity 0.8.24, deployed via py-solc-x + web3.py
- **SDK**: TypeScript (viem) — 16 methods, human-readable USDC conversion
- **MCP Server**: 10 tools for AI agent integration
- **Frontend**: 3 pages in agent-hub-main (/factory, /factory/templates, /factory/[agentId])

## Deployment History

| Version | Date | Notes |
|---------|------|-------|
| V1 | 2026-06-05 | Initial deploy — failed because Identity V1 had no transfer function |
| V2 | 2026-06-05 | Identity V2 (transferAgent) + Factory V2 — e2e tests passing |
| V3 | 2026-06-05 | Full stack redeploy — all 8 layers pointing to Identity V2 |

## Scripts

- `scripts/deploy.py` — compile + deploy Factory to Arc Testnet
- `scripts/e2e_test.py` — 7 on-chain tests (template, deploy, profile, stats)
- `scripts/redeploy/deploy_v2.py` — deploy Identity V2 + Factory V2
- `scripts/redeploy/redeploy_all.py` — full 8-layer redeploy from GitHub sources
- `scripts/redeploy/AgentIdentityV2.sol` — Identity with transferAgent + approve

## License

MIT
