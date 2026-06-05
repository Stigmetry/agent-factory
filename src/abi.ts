// ─── AgentFactory ABI ─────────────────────────────────────────────────────
// Auto-generated from compiled contract — 26 entries

export const AGENT_FACTORY_ABI = [
  // ── Deploy ──────────────────────────────────────────────────────────────
  {
    type: "function",
    name: "deployAgent",
    inputs: [
      {
        name: "config",
        type: "tuple",
        components: [
          { name: "name", type: "string" },
          { name: "metadataURI", type: "string" },
          { name: "listOnMarket", type: "bool" },
          { name: "hourlyRateUsdc", type: "uint256" },
          { name: "capabilities", type: "bytes32[]" },
          { name: "availableUntil", type: "uint256" },
          { name: "createRetainerPlan", type: "bool" },
          { name: "retainerPriceUsdc", type: "uint256" },
          { name: "retainerInterval", type: "uint256" },
          { name: "retainerDescription", type: "string" },
          { name: "stakeCollateral", type: "bool" },
          { name: "stakeAmountUsdc", type: "uint256" },
        ],
      },
    ],
    outputs: [{ name: "agentTokenId", type: "uint256" }],
    stateMutability: "nonpayable",
  },
  {
    type: "function",
    name: "deployFromTemplate",
    inputs: [
      { name: "templateId", type: "uint256" },
      { name: "name", type: "string" },
      { name: "metadataURI", type: "string" },
      { name: "enableMarket", type: "bool" },
      { name: "enableRetainer", type: "bool" },
      { name: "enableStaking", type: "bool" },
    ],
    outputs: [{ name: "agentTokenId", type: "uint256" }],
    stateMutability: "nonpayable",
  },

  // ── Templates ───────────────────────────────────────────────────────────
  {
    type: "function",
    name: "createTemplate",
    inputs: [
      {
        name: "config",
        type: "tuple",
        components: [
          { name: "name", type: "string" },
          { name: "description", type: "string" },
          { name: "defaultMetadataURI", type: "string" },
          { name: "suggestedHourlyRate", type: "uint256" },
          { name: "defaultCapabilities", type: "bytes32[]" },
          { name: "suggestedRetainerPrice", type: "uint256" },
          { name: "suggestedRetainerInterval", type: "uint256" },
          { name: "suggestedStakeAmount", type: "uint256" },
        ],
      },
    ],
    outputs: [{ name: "templateId", type: "uint256" }],
    stateMutability: "nonpayable",
  },
  {
    type: "function",
    name: "updateTemplate",
    inputs: [
      { name: "templateId", type: "uint256" },
      {
        name: "config",
        type: "tuple",
        components: [
          { name: "name", type: "string" },
          { name: "description", type: "string" },
          { name: "defaultMetadataURI", type: "string" },
          { name: "suggestedHourlyRate", type: "uint256" },
          { name: "defaultCapabilities", type: "bytes32[]" },
          { name: "suggestedRetainerPrice", type: "uint256" },
          { name: "suggestedRetainerInterval", type: "uint256" },
          { name: "suggestedStakeAmount", type: "uint256" },
        ],
      },
    ],
    outputs: [],
    stateMutability: "nonpayable",
  },
  {
    type: "function",
    name: "deactivateTemplate",
    inputs: [{ name: "templateId", type: "uint256" }],
    outputs: [],
    stateMutability: "nonpayable",
  },

  // ── Views ───────────────────────────────────────────────────────────────
  {
    type: "function",
    name: "getTemplate",
    inputs: [{ name: "templateId", type: "uint256" }],
    outputs: [
      {
        name: "",
        type: "tuple",
        components: [
          { name: "id", type: "uint256" },
          { name: "name", type: "string" },
          { name: "description", type: "string" },
          { name: "defaultMetadataURI", type: "string" },
          { name: "suggestedHourlyRate", type: "uint256" },
          { name: "defaultCapabilities", type: "bytes32[]" },
          { name: "suggestedRetainerPrice", type: "uint256" },
          { name: "suggestedRetainerInterval", type: "uint256" },
          { name: "suggestedStakeAmount", type: "uint256" },
          { name: "active", type: "bool" },
          { name: "creator", type: "address" },
          { name: "createdAt", type: "uint256" },
          { name: "useCount", type: "uint256" },
        ],
      },
    ],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "getActiveTemplates",
    inputs: [],
    outputs: [{ name: "templateIds", type: "uint256[]" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "getDeployedAgent",
    inputs: [{ name: "agentTokenId", type: "uint256" }],
    outputs: [
      {
        name: "",
        type: "tuple",
        components: [
          { name: "agentTokenId", type: "uint256" },
          { name: "owner", type: "address" },
          { name: "templateId", type: "uint256" },
          { name: "listedOnMarket", type: "bool" },
          { name: "retainerPlanId", type: "uint256" },
          { name: "hasStake", type: "bool" },
          { name: "deployedAt", type: "uint256" },
        ],
      },
    ],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "getAgentsByOwner",
    inputs: [{ name: "ownerAddr", type: "address" }],
    outputs: [{ name: "agentTokenIds", type: "uint256[]" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "getFactoryStats",
    inputs: [],
    outputs: [
      { name: "_totalAgentsDeployed", type: "uint256" },
      { name: "_totalTemplates", type: "uint256" },
      { name: "_totalActiveTemplates", type: "uint256" },
    ],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "getAgentProfile",
    inputs: [{ name: "agentTokenId", type: "uint256" }],
    outputs: [
      { name: "name", type: "string" },
      { name: "reputation", type: "uint256" },
      { name: "isListed", type: "bool" },
      { name: "hourlyRate", type: "uint256" },
      { name: "stakeAmount", type: "uint256" },
      { name: "retainerPlanId", type: "uint256" },
    ],
    stateMutability: "view",
  },

  // ── State vars ──────────────────────────────────────────────────────────
  {
    type: "function",
    name: "owner",
    inputs: [],
    outputs: [{ name: "", type: "address" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "totalAgentsDeployed",
    inputs: [],
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "totalTemplates",
    inputs: [],
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "identity",
    inputs: [],
    outputs: [{ name: "", type: "address" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "market",
    inputs: [],
    outputs: [{ name: "", type: "address" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "retainer",
    inputs: [],
    outputs: [{ name: "", type: "address" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "staking",
    inputs: [],
    outputs: [{ name: "", type: "address" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "usdc",
    inputs: [],
    outputs: [{ name: "", type: "address" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "transferOwnership",
    inputs: [{ name: "newOwner", type: "address" }],
    outputs: [],
    stateMutability: "nonpayable",
  },

  // ── Events ──────────────────────────────────────────────────────────────
  {
    type: "event",
    name: "AgentDeployed",
    inputs: [
      { name: "agentTokenId", type: "uint256", indexed: true },
      { name: "owner", type: "address", indexed: true },
      { name: "templateId", type: "uint256", indexed: true },
      { name: "name", type: "string", indexed: false },
    ],
  },
  {
    type: "event",
    name: "TemplateCreated",
    inputs: [
      { name: "templateId", type: "uint256", indexed: true },
      { name: "creator", type: "address", indexed: true },
      { name: "name", type: "string", indexed: false },
    ],
  },
  {
    type: "event",
    name: "TemplateUpdated",
    inputs: [{ name: "templateId", type: "uint256", indexed: true }],
  },
  {
    type: "event",
    name: "TemplateDeactivated",
    inputs: [{ name: "templateId", type: "uint256", indexed: true }],
  },
] as const;

// ─── USDC ERC-20 ABI (minimal for approve) ───────────────────────────────

export const USDC_ABI = [
  {
    type: "function",
    name: "approve",
    inputs: [
      { name: "spender", type: "address" },
      { name: "amount", type: "uint256" },
    ],
    outputs: [{ name: "", type: "bool" }],
    stateMutability: "nonpayable",
  },
  {
    type: "function",
    name: "allowance",
    inputs: [
      { name: "owner", type: "address" },
      { name: "spender", type: "address" },
    ],
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
  },
  {
    type: "function",
    name: "balanceOf",
    inputs: [{ name: "account", type: "address" }],
    outputs: [{ name: "", type: "uint256" }],
    stateMutability: "view",
  },
] as const;
