import {
  createPublicClient,
  createWalletClient,
  http,
  keccak256,
  toHex,
  parseUnits,
  formatUnits,
  type PublicClient,
  type WalletClient,
  type Address,
  type Hash,
  type Account,
  type Chain,
} from "viem";
import { arcTestnet, CONTRACTS } from "./config.js";
import { AGENT_FACTORY_ABI, USDC_ABI } from "./abi.js";

// ─── Types ────────────────────────────────────────────────────────────────

export interface DeployConfig {
  name: string;
  metadataURI: string;
  // Market listing (optional)
  listOnMarket?: boolean;
  hourlyRateUsdc?: number;       // human-readable USDC (e.g. 50 = $50/hr)
  capabilities?: string[];       // plain-text tags — auto-hashed to bytes32
  availableUntil?: number;       // unix timestamp (0 = indefinite)
  // Retainer plan (optional)
  createRetainerPlan?: boolean;
  retainerPriceUsdc?: number;    // human-readable USDC per interval
  retainerIntervalSeconds?: number;
  retainerDescription?: string;
  // Staking (optional)
  stakeCollateral?: boolean;
  stakeAmountUsdc?: number;      // human-readable USDC
}

export interface TemplateConfig {
  name: string;
  description: string;
  defaultMetadataURI: string;
  suggestedHourlyRate?: number;
  defaultCapabilities?: string[];
  suggestedRetainerPrice?: number;
  suggestedRetainerInterval?: number;
  suggestedStakeAmount?: number;
}

export interface AgentTemplate {
  id: bigint;
  name: string;
  description: string;
  defaultMetadataURI: string;
  suggestedHourlyRate: bigint;
  defaultCapabilities: `0x${string}`[];
  suggestedRetainerPrice: bigint;
  suggestedRetainerInterval: bigint;
  suggestedStakeAmount: bigint;
  active: boolean;
  creator: Address;
  createdAt: bigint;
  useCount: bigint;
}

export interface DeployedAgent {
  agentTokenId: bigint;
  owner: Address;
  templateId: bigint;
  listedOnMarket: boolean;
  retainerPlanId: bigint;
  hasStake: boolean;
  deployedAt: bigint;
}

export interface AgentProfile {
  name: string;
  reputation: bigint;
  reputationPercent: number;
  isListed: boolean;
  hourlyRate: bigint;
  hourlyRateUsdc: number;
  stakeAmount: bigint;
  stakeAmountUsdc: number;
  retainerPlanId: bigint;
}

export interface FactoryStats {
  totalAgentsDeployed: bigint;
  totalTemplates: bigint;
  totalActiveTemplates: bigint;
}

// ─── Helper ───────────────────────────────────────────────────────────────

/** Hash a capability string to bytes32 (matches Solidity keccak256) */
export function hashCapability(cap: string): `0x${string}` {
  return keccak256(toHex(cap));
}

/** Convert human USDC (e.g. 50) to 6-decimal on-chain units */
function toUsdc6(amount: number): bigint {
  return parseUnits(amount.toString(), 6);
}

/** Convert 6-decimal on-chain USDC to human-readable number */
function fromUsdc6(amount: bigint): number {
  return Number(formatUnits(amount, 6));
}

// ─── Client ───────────────────────────────────────────────────────────────

export class AgentFactoryClient {
  public readonly publicClient: PublicClient;
  public readonly walletClient: WalletClient | null;
  public readonly factoryAddress: Address;

  constructor(opts?: {
    rpcUrl?: string;
    walletClient?: WalletClient;
    factoryAddress?: Address;
  }) {
    this.factoryAddress = opts?.factoryAddress ?? CONTRACTS.factory;

    this.publicClient = createPublicClient({
      chain: arcTestnet as Chain,
      transport: http(opts?.rpcUrl ?? "https://rpc.testnet.arc.network"),
    });

    this.walletClient = opts?.walletClient ?? null;
  }

  // ── Helpers ─────────────────────────────────────────────────────────────

  private requireWallet(): WalletClient & { account: Account } {
    if (!this.walletClient?.account) {
      throw new Error("Wallet client with account required for write operations");
    }
    return this.walletClient as WalletClient & { account: Account };
  }

  // ── Deploy ──────────────────────────────────────────────────────────────

  /** Deploy a new agent with full custom config — single transaction */
  async deployAgent(config: DeployConfig): Promise<{ txHash: Hash; agentTokenId?: bigint }> {
    const wallet = this.requireWallet();

    // If staking, approve USDC first
    if (config.stakeCollateral && config.stakeAmountUsdc) {
      const approveHash = await wallet.writeContract({
        address: CONTRACTS.usdc,
        abi: USDC_ABI,
        functionName: "approve",
        args: [this.factoryAddress, toUsdc6(config.stakeAmountUsdc)],
        chain: arcTestnet as Chain,
      });
      await this.publicClient.waitForTransactionReceipt({ hash: approveHash });
    }

    const onChainConfig = {
      name: config.name,
      metadataURI: config.metadataURI,
      listOnMarket: config.listOnMarket ?? false,
      hourlyRateUsdc: config.hourlyRateUsdc ? toUsdc6(config.hourlyRateUsdc) : 0n,
      capabilities: (config.capabilities ?? []).map(hashCapability),
      availableUntil: BigInt(config.availableUntil ?? 0),
      createRetainerPlan: config.createRetainerPlan ?? false,
      retainerPriceUsdc: config.retainerPriceUsdc ? toUsdc6(config.retainerPriceUsdc) : 0n,
      retainerInterval: BigInt(config.retainerIntervalSeconds ?? 0),
      retainerDescription: config.retainerDescription ?? "",
      stakeCollateral: config.stakeCollateral ?? false,
      stakeAmountUsdc: config.stakeAmountUsdc ? toUsdc6(config.stakeAmountUsdc) : 0n,
    };

    const txHash = await wallet.writeContract({
      address: this.factoryAddress,
      abi: AGENT_FACTORY_ABI,
      functionName: "deployAgent",
      args: [onChainConfig],
      chain: arcTestnet as Chain,
    });

    return { txHash };
  }

  /** Deploy from a pre-configured template */
  async deployFromTemplate(
    templateId: bigint,
    name: string,
    metadataURI: string,
    opts?: { enableMarket?: boolean; enableRetainer?: boolean; enableStaking?: boolean }
  ): Promise<{ txHash: Hash }> {
    const wallet = this.requireWallet();

    // If staking enabled, check template for amount and approve
    if (opts?.enableStaking) {
      const tmpl = await this.getTemplate(templateId);
      if (tmpl.suggestedStakeAmount > 0n) {
        const approveHash = await wallet.writeContract({
          address: CONTRACTS.usdc,
          abi: USDC_ABI,
          functionName: "approve",
          args: [this.factoryAddress, tmpl.suggestedStakeAmount],
          chain: arcTestnet as Chain,
        });
        await this.publicClient.waitForTransactionReceipt({ hash: approveHash });
      }
    }

    const txHash = await wallet.writeContract({
      address: this.factoryAddress,
      abi: AGENT_FACTORY_ABI,
      functionName: "deployFromTemplate",
      args: [
        templateId,
        name,
        metadataURI,
        opts?.enableMarket ?? true,
        opts?.enableRetainer ?? true,
        opts?.enableStaking ?? false,
      ],
      chain: arcTestnet as Chain,
    });

    return { txHash };
  }

  // ── Templates ───────────────────────────────────────────────────────────

  /** Create a new agent template */
  async createTemplate(config: TemplateConfig): Promise<{ txHash: Hash }> {
    const wallet = this.requireWallet();

    const txHash = await wallet.writeContract({
      address: this.factoryAddress,
      abi: AGENT_FACTORY_ABI,
      functionName: "createTemplate",
      args: [
        {
          name: config.name,
          description: config.description,
          defaultMetadataURI: config.defaultMetadataURI,
          suggestedHourlyRate: config.suggestedHourlyRate ? toUsdc6(config.suggestedHourlyRate) : 0n,
          defaultCapabilities: (config.defaultCapabilities ?? []).map(hashCapability),
          suggestedRetainerPrice: config.suggestedRetainerPrice ? toUsdc6(config.suggestedRetainerPrice) : 0n,
          suggestedRetainerInterval: BigInt(config.suggestedRetainerInterval ?? 0),
          suggestedStakeAmount: config.suggestedStakeAmount ? toUsdc6(config.suggestedStakeAmount) : 0n,
        },
      ],
      chain: arcTestnet as Chain,
    });

    return { txHash };
  }

  /** Get a template by ID */
  async getTemplate(templateId: bigint): Promise<AgentTemplate> {
    const result = await this.publicClient.readContract({
      address: this.factoryAddress,
      abi: AGENT_FACTORY_ABI,
      functionName: "getTemplate",
      args: [templateId],
    });
    return result as unknown as AgentTemplate;
  }

  /** List all active template IDs */
  async getActiveTemplates(): Promise<bigint[]> {
    const result = await this.publicClient.readContract({
      address: this.factoryAddress,
      abi: AGENT_FACTORY_ABI,
      functionName: "getActiveTemplates",
    });
    return result as bigint[];
  }

  /** List all active templates with full details */
  async listTemplates(): Promise<AgentTemplate[]> {
    const ids = await this.getActiveTemplates();
    return Promise.all(ids.map((id) => this.getTemplate(id)));
  }

  // ── Agent Views ─────────────────────────────────────────────────────────

  /** Get factory deployment record for an agent */
  async getDeployedAgent(agentTokenId: bigint): Promise<DeployedAgent> {
    const result = await this.publicClient.readContract({
      address: this.factoryAddress,
      abi: AGENT_FACTORY_ABI,
      functionName: "getDeployedAgent",
      args: [agentTokenId],
    });
    return result as unknown as DeployedAgent;
  }

  /** Get cross-layer agent profile (identity + market + staking) */
  async getAgentProfile(agentTokenId: bigint): Promise<AgentProfile> {
    const result = (await this.publicClient.readContract({
      address: this.factoryAddress,
      abi: AGENT_FACTORY_ABI,
      functionName: "getAgentProfile",
      args: [agentTokenId],
    })) as [string, bigint, boolean, bigint, bigint, bigint];

    const [name, reputation, isListed, hourlyRate, stakeAmount, retainerPlanId] = result;

    return {
      name,
      reputation,
      reputationPercent: Number(reputation) / 100, // bps → %
      isListed,
      hourlyRate,
      hourlyRateUsdc: fromUsdc6(hourlyRate),
      stakeAmount,
      stakeAmountUsdc: fromUsdc6(stakeAmount),
      retainerPlanId,
    };
  }

  /** Get all agents deployed by an owner */
  async getAgentsByOwner(owner: Address): Promise<bigint[]> {
    const result = await this.publicClient.readContract({
      address: this.factoryAddress,
      abi: AGENT_FACTORY_ABI,
      functionName: "getAgentsByOwner",
      args: [owner],
    });
    return result as bigint[];
  }

  /** Get factory-wide stats */
  async getFactoryStats(): Promise<FactoryStats> {
    const result = (await this.publicClient.readContract({
      address: this.factoryAddress,
      abi: AGENT_FACTORY_ABI,
      functionName: "getFactoryStats",
    })) as [bigint, bigint, bigint];

    return {
      totalAgentsDeployed: result[0],
      totalTemplates: result[1],
      totalActiveTemplates: result[2],
    };
  }
}
