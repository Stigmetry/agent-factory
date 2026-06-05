#!/usr/bin/env node
/**
 * Arc Agent Factory — MCP Server
 * Layer 8 tools for deploying and managing agents across the full stack.
 *
 * 10 tools:
 *   deploy-agent, deploy-from-template,
 *   create-template, list-templates, get-template,
 *   get-agent-profile, get-deployed-agent, get-agents-by-owner,
 *   get-factory-stats, hash-capability
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { createWalletClient, http, type Address } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { AgentFactoryClient, hashCapability } from "../client.js";
import { arcTestnet } from "../config.js";

// ─── Init ─────────────────────────────────────────────────────────────────

const PRIVATE_KEY = process.env.ARC_PRIVATE_KEY;

function getClient(needsWallet = false): AgentFactoryClient {
  if (needsWallet && !PRIVATE_KEY) {
    throw new Error("ARC_PRIVATE_KEY env var required for write operations");
  }

  const walletClient = PRIVATE_KEY
    ? createWalletClient({
        account: privateKeyToAccount(`0x${PRIVATE_KEY.replace(/^0x/, "")}`),
        chain: arcTestnet,
        transport: http("https://rpc.testnet.arc.network"),
      })
    : undefined;

  return new AgentFactoryClient({ walletClient });
}

const server = new McpServer({
  name: "arc-agent-factory",
  version: "1.0.0",
});

// ─── Deploy Tools ─────────────────────────────────────────────────────────

server.tool(
  "deploy-agent",
  "Deploy a new agent across the Arc 7-layer stack in a single transaction. " +
    "Registers ERC-8004 identity, optionally lists on market, creates retainer plan, stakes USDC.",
  {
    name: z.string().describe("Agent name"),
    metadataURI: z.string().describe("Agent metadata URI (IPFS or HTTPS)"),
    listOnMarket: z.boolean().optional().describe("List on AgentMarket"),
    hourlyRateUsdc: z.number().optional().describe("Hourly rate in USDC"),
    capabilities: z.array(z.string()).optional().describe("Capability tags"),
    createRetainerPlan: z.boolean().optional().describe("Create retainer plan"),
    retainerPriceUsdc: z.number().optional().describe("Retainer price in USDC"),
    retainerIntervalSeconds: z.number().optional().describe("Retainer interval in seconds"),
    retainerDescription: z.string().optional().describe("Retainer plan description"),
    stakeCollateral: z.boolean().optional().describe("Stake USDC collateral"),
    stakeAmountUsdc: z.number().optional().describe("Stake amount in USDC"),
  },
  async (args) => {
    const client = getClient(true);
    const result = await client.deployAgent(args);
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              success: true,
              txHash: result.txHash,
              message: `Agent "${args.name}" deployment submitted. TX: ${result.txHash}`,
              explorer: `https://testnet.arcscan.app/tx/${result.txHash}`,
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

server.tool(
  "deploy-from-template",
  "Deploy an agent using a pre-configured template. One-click setup with template defaults.",
  {
    templateId: z.number().describe("Template ID"),
    name: z.string().describe("Agent name"),
    metadataURI: z.string().optional().describe("Metadata URI (empty = use template default)"),
    enableMarket: z.boolean().optional().describe("Enable market listing"),
    enableRetainer: z.boolean().optional().describe("Enable retainer plan"),
    enableStaking: z.boolean().optional().describe("Enable USDC staking"),
  },
  async (args) => {
    const client = getClient(true);
    const result = await client.deployFromTemplate(
      BigInt(args.templateId),
      args.name,
      args.metadataURI ?? "",
      {
        enableMarket: args.enableMarket,
        enableRetainer: args.enableRetainer,
        enableStaking: args.enableStaking,
      }
    );
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              success: true,
              txHash: result.txHash,
              templateId: args.templateId,
              message: `Agent "${args.name}" deployed from template #${args.templateId}`,
              explorer: `https://testnet.arcscan.app/tx/${result.txHash}`,
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ─── Template Tools ───────────────────────────────────────────────────────

server.tool(
  "create-template",
  "Create a new agent template for one-click deployments.",
  {
    name: z.string().describe("Template name (e.g. 'Freelance Developer')"),
    description: z.string().describe("Template description"),
    defaultMetadataURI: z.string().describe("Default metadata URI"),
    suggestedHourlyRate: z.number().optional().describe("Suggested hourly rate in USDC"),
    defaultCapabilities: z.array(z.string()).optional().describe("Default capability tags"),
    suggestedRetainerPrice: z.number().optional().describe("Suggested retainer price in USDC"),
    suggestedRetainerInterval: z.number().optional().describe("Suggested retainer interval in seconds"),
    suggestedStakeAmount: z.number().optional().describe("Suggested stake amount in USDC"),
  },
  async (args) => {
    const client = getClient(true);
    const result = await client.createTemplate(args);
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              success: true,
              txHash: result.txHash,
              message: `Template "${args.name}" created`,
              explorer: `https://testnet.arcscan.app/tx/${result.txHash}`,
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

server.tool(
  "list-templates",
  "List all active agent templates available for deployment.",
  {},
  async () => {
    const client = getClient();
    const templates = await client.listTemplates();
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              count: templates.length,
              templates: templates.map((t) => ({
                id: Number(t.id),
                name: t.name,
                description: t.description,
                suggestedHourlyRate: Number(t.suggestedHourlyRate) / 1e6,
                suggestedRetainerPrice: Number(t.suggestedRetainerPrice) / 1e6,
                suggestedStakeAmount: Number(t.suggestedStakeAmount) / 1e6,
                useCount: Number(t.useCount),
                creator: t.creator,
              })),
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

server.tool(
  "get-template",
  "Get full details of an agent template.",
  { templateId: z.number().describe("Template ID") },
  async (args) => {
    const client = getClient();
    const tmpl = await client.getTemplate(BigInt(args.templateId));
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              id: Number(tmpl.id),
              name: tmpl.name,
              description: tmpl.description,
              defaultMetadataURI: tmpl.defaultMetadataURI,
              suggestedHourlyRate: Number(tmpl.suggestedHourlyRate) / 1e6,
              capabilities: tmpl.defaultCapabilities,
              suggestedRetainerPrice: Number(tmpl.suggestedRetainerPrice) / 1e6,
              suggestedRetainerInterval: Number(tmpl.suggestedRetainerInterval),
              suggestedStakeAmount: Number(tmpl.suggestedStakeAmount) / 1e6,
              active: tmpl.active,
              creator: tmpl.creator,
              useCount: Number(tmpl.useCount),
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ─── Agent Profile Tools ──────────────────────────────────────────────────

server.tool(
  "get-agent-profile",
  "Get a cross-layer agent profile — identity, market listing, staking, retainer — all in one call.",
  { agentTokenId: z.number().describe("ERC-8004 agent token ID") },
  async (args) => {
    const client = getClient();
    const profile = await client.getAgentProfile(BigInt(args.agentTokenId));
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              name: profile.name,
              reputation: `${profile.reputationPercent}%`,
              isListed: profile.isListed,
              hourlyRateUsdc: profile.hourlyRateUsdc,
              stakeAmountUsdc: profile.stakeAmountUsdc,
              retainerPlanId: Number(profile.retainerPlanId),
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

server.tool(
  "get-deployed-agent",
  "Get factory deployment record for an agent (template used, layers configured).",
  { agentTokenId: z.number().describe("ERC-8004 agent token ID") },
  async (args) => {
    const client = getClient();
    const agent = await client.getDeployedAgent(BigInt(args.agentTokenId));
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              agentTokenId: Number(agent.agentTokenId),
              owner: agent.owner,
              templateId: Number(agent.templateId),
              listedOnMarket: agent.listedOnMarket,
              retainerPlanId: Number(agent.retainerPlanId),
              hasStake: agent.hasStake,
              deployedAt: Number(agent.deployedAt),
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

server.tool(
  "get-agents-by-owner",
  "List all agents deployed by a specific wallet address.",
  { owner: z.string().describe("Wallet address") },
  async (args) => {
    const client = getClient();
    const ids = await client.getAgentsByOwner(args.owner as Address);
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              owner: args.owner,
              count: ids.length,
              agentTokenIds: ids.map(Number),
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ─── Stats & Utility ──────────────────────────────────────────────────────

server.tool(
  "get-factory-stats",
  "Get factory-wide statistics: total agents deployed, templates created.",
  {},
  async () => {
    const client = getClient();
    const stats = await client.getFactoryStats();
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              totalAgentsDeployed: Number(stats.totalAgentsDeployed),
              totalTemplates: Number(stats.totalTemplates),
              totalActiveTemplates: Number(stats.totalActiveTemplates),
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

server.tool(
  "hash-capability",
  "Hash a capability string to bytes32 for use in market listings and templates.",
  { capability: z.string().describe("Capability tag (e.g. 'solidity-development')") },
  async (args) => {
    const hash = hashCapability(args.capability);
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify({ capability: args.capability, hash }, null, 2),
        },
      ],
    };
  }
);

// ─── Start ────────────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Arc Agent Factory MCP server running on stdio");
}

main().catch(console.error);
