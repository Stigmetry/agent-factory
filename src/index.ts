// Arc Agent Factory — Layer 8 SDK
// One-click agent deployment across the 7-layer agentic commerce stack

export { AgentFactoryClient, hashCapability } from "./client.js";
export { arcTestnet, CONTRACTS } from "./config.js";
export { AGENT_FACTORY_ABI, USDC_ABI } from "./abi.js";

export type {
  DeployConfig,
  TemplateConfig,
  AgentTemplate,
  DeployedAgent,
  AgentProfile,
  FactoryStats,
} from "./client.js";
