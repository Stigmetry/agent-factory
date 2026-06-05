import { defineChain } from "viem";

// ─── Arc Testnet Chain Definition ─────────────────────────────────────────

export const arcTestnet = defineChain({
  id: 5042002,
  name: "Arc Testnet",
  nativeCurrency: { name: "USDC", symbol: "USDC", decimals: 18 },
  rpcUrls: {
    default: { http: ["https://rpc.testnet.arc.network"] },
  },
  blockExplorers: {
    default: { name: "Arcscan", url: "https://testnet.arcscan.app" },
  },
  testnet: true,
});

// ─── Deployed Contract Addresses ──────────────────────────────────────────

export const CONTRACTS = {
  /** Layer 8 — AgentFactory (V3) */
  factory: "0x1e2e8abfa05b0df0c83af5de3580a79f6c7f6398" as const,
  /** Layer 1 — AgentIdentity (ERC-8004 V2 with transferAgent) */
  identity: "0x0bf50994245ab3297ed95665d62192977930fabb" as const,
  /** Layer 2 — AgentJob (ERC-8183) */
  job: "0x2747fc4601933c7bdfeaddf52808a1c0bedc2323" as const,
  /** Layer 3 — AgentMarket */
  market: "0x79718fbd092276124d5bfed596e91f861d78a547" as const,
  /** Layer 4 — AgentOrchestrator */
  orchestrator: "0x925a80a447dddb7726a24fabc07fd22b76c4e7c1" as const,
  /** Layer 5 — AgentRetainer */
  retainer: "0x9ca8bf8a090a2607d14e6cb0228e02ebd3d3329d" as const,
  /** Layer 6 — AgentStaking */
  staking: "0xbbab7b7ed776e169eb6f0284d97f03cef3c5ecef" as const,
  /** Layer 7 — AgentDAO */
  dao: "0x256658aa7be4e4a066d002f9fecd8e60f8efcbb7" as const,
  /** USDC ERC-20 interface on Arc */
  usdc: "0x3600000000000000000000000000000000000000" as const,
} as const;
