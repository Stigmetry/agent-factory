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
  /** Layer 8 — AgentFactory */
  factory: "0x3c606d295a18250eaf889f10158315532c6e827f" as const,
  /** Layer 1 — AgentIdentity (ERC-8004) */
  identity: "0x5Bef356f89425823FC7eebB3A6ED1A678F3b8233" as const,
  /** Layer 2 — AgentJob (ERC-8183) */
  job: "0xD698d15F776279c0213444a779941e8E0Cbe5094" as const,
  /** Layer 3 — AgentMarket */
  market: "0x6BAf93EB026b7BC3db651065302D1934Ad577ec1" as const,
  /** Layer 4 — AgentOrchestrator */
  orchestrator: "0xbA99f039b7892d9F546253444c95EDea822471b0" as const,
  /** Layer 5 — AgentRetainer */
  retainer: "0x5C80B95Ac3c2eE748F427aBB15Ad5d3E94fcD8D6" as const,
  /** Layer 6 — AgentStaking */
  staking: "0x0107BD44E269888F12dCc32E9bc03E79Ca7Be770" as const,
  /** Layer 7 — AgentDAO */
  dao: "0x213157853e67BC17F4b69B8F3f5b0fe14C64fCf7" as const,
  /** USDC ERC-20 interface on Arc */
  usdc: "0x3600000000000000000000000000000000000000" as const,
} as const;
