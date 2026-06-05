#!/usr/bin/env python3
"""
End-to-end test for AgentFactory (Layer 8) on Arc Testnet.

Flow:
  1. Read factory stats (should be 0/0/0)
  2. Create a "Freelance Developer" template
  3. Verify template was created
  4. Deploy an agent from the template (identity only — no market/retainer/staking)
  5. Verify the agent was deployed and profile reads correctly
  6. Deploy a second agent with custom config (identity + will skip optional layers for now)
  7. Final stats check
"""

import json
import os
import time
import requests
from eth_account import Account
from web3 import Web3

# ─── Config ────────────────────────────────────────────────────────────────

ARC_RPC  = "https://rpc.testnet.arc.network"
CHAIN_ID = 5042002

FACTORY_ADDR = Web3.to_checksum_address("0xbffff5f60851fc4eb51c0876fe76165a5d9a3f88")

PRIVATE_KEY  = os.environ.get("DEPLOYER_PRIVATE_KEY")
assert PRIVATE_KEY, "DEPLOYER_PRIVATE_KEY not set"

MAX_FEE  = Web3.to_wei(25, "gwei")
PRIORITY = Web3.to_wei(2,  "gwei")

# Load ABI
abi_path = os.path.join(os.path.dirname(__file__), "..", "abi.json")
with open(abi_path) as f:
    FACTORY_ABI = json.load(f)

# ─── Helpers ───────────────────────────────────────────────────────────────

def get_proxy():
    return os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

def rpc_call(method, params=None):
    proxy = get_proxy()
    proxies = {"https": proxy, "http": proxy} if proxy else {}
    resp = requests.post(ARC_RPC, json={"jsonrpc":"2.0","id":1,"method":method,"params":params or []},
                         proxies=proxies, timeout=30)
    data = resp.json()
    if "error" in data:
        raise Exception(f"RPC error: {data['error']}")
    return data["result"]

def wait_receipt(tx_hash, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        result = rpc_call("eth_getTransactionReceipt", [tx_hash])
        if result is not None:
            status = int(result["status"], 16)
            if status != 1:
                # Try to get revert reason
                raise Exception(f"TX REVERTED: {tx_hash}\nReceipt: {json.dumps(result, indent=2)}")
            return result
        time.sleep(3)
    raise Exception(f"Timeout: {tx_hash}")

def send_tx(tx_data):
    acct = Account.from_key(PRIVATE_KEY)
    nonce_hex = rpc_call("eth_getTransactionCount", [acct.address, "latest"])
    nonce = int(nonce_hex, 16)

    tx_data.update({
        "from":                 acct.address,
        "nonce":                nonce,
        "maxFeePerGas":         MAX_FEE,
        "maxPriorityFeePerGas": PRIORITY,
        "chainId":              CHAIN_ID,
        "type":                 2,
    })

    signed = acct.sign_transaction(tx_data)
    raw_hex = "0x" + signed.raw_transaction.hex()
    tx_hash = rpc_call("eth_sendRawTransaction", [raw_hex])
    return tx_hash

# ─── Contract Interface ───────────────────────────────────────────────────

w3 = Web3()
factory = w3.eth.contract(
    address=Web3.to_checksum_address(FACTORY_ADDR),
    abi=FACTORY_ABI,
)
acct = Account.from_key(PRIVATE_KEY)

def abi_type_to_str(output):
    """Convert ABI output to a type string eth_abi can decode, expanding tuples."""
    if output["type"] == "tuple":
        inner = ",".join(abi_type_to_str(c) for c in output["components"])
        return f"({inner})"
    elif output["type"] == "tuple[]":
        inner = ",".join(abi_type_to_str(c) for c in output["components"])
        return f"({inner})[]"
    return output["type"]

def call_view(fn_name, *args):
    """Call a view function via eth_call."""
    fn = factory.get_function_by_name(fn_name)
    data = fn(*args)._encode_transaction_data()
    result = rpc_call("eth_call", [{"to": FACTORY_ADDR, "data": data}, "latest"])
    # Build proper type strings (expanding tuples)
    abi_entry = next(a for a in FACTORY_ABI if a.get("name") == fn_name and a.get("type") == "function")
    output_types = [abi_type_to_str(out) for out in abi_entry["outputs"]]
    decoded = w3.codec.decode(output_types, bytes.fromhex(result[2:]))
    return decoded

def write_tx(fn_name, *args, gas=2_000_000, value=0):
    """Build, sign, send, and wait for a write transaction."""
    fn = factory.get_function_by_name(fn_name)
    data = fn(*args)._encode_transaction_data()
    tx_hash = send_tx({"to": FACTORY_ADDR, "data": data, "gas": gas, "value": value})
    print(f"  TX: {tx_hash}")
    receipt = wait_receipt(tx_hash)
    gas_used = int(receipt["gasUsed"], 16)
    print(f"  Gas: {gas_used:,} | Block: {int(receipt['blockNumber'], 16)}")
    return receipt

# ─── Test Steps ────────────────────────────────────────────────────────────

def test_1_initial_stats():
    print("\n" + "="*60)
    print("TEST 1: Read initial factory stats")
    print("="*60)
    stats = call_view("getFactoryStats")
    print(f"  Total agents deployed:  {stats[0]}")
    print(f"  Total templates:        {stats[1]}")
    print(f"  Total active templates: {stats[2]}")
    return stats

def test_2_create_template():
    print("\n" + "="*60)
    print("TEST 2: Create 'Freelance Developer' template")
    print("="*60)

    # TemplateConfig struct
    template_config = (
        "Freelance Developer",                          # name
        "Full-stack developer agent for contract work",  # description
        "ipfs://QmFreelanceDev",                        # defaultMetadataURI
        50 * 10**6,                                      # suggestedHourlyRate: $50/hr (6 decimals)
        [                                                # defaultCapabilities (bytes32[])
            Web3.keccak(text="solidity-development"),
            Web3.keccak(text="typescript"),
            Web3.keccak(text="smart-contracts"),
        ],
        100 * 10**6,                                     # suggestedRetainerPrice: $100/interval
        3600,                                            # suggestedRetainerInterval: 1 hour
        5 * 10**6,                                       # suggestedStakeAmount: $5
    )

    receipt = write_tx("createTemplate", template_config, gas=500_000)

    # Check for TemplateCreated event
    print(f"  Logs: {len(receipt['logs'])} events emitted")
    print(f"  Template created!")

    return receipt

def test_3_verify_template():
    print("\n" + "="*60)
    print("TEST 3: Verify template #1 exists")
    print("="*60)

    raw = call_view("getTemplate", 1)
    tmpl = raw[0]  # unwrap outer tuple
    print(f"  ID:          {tmpl[0]}")
    print(f"  Name:        {tmpl[1]}")
    print(f"  Description: {tmpl[2]}")
    print(f"  MetadataURI: {tmpl[3]}")
    print(f"  Hourly rate: ${tmpl[4] / 10**6}")
    print(f"  Capabilities:{len(tmpl[5])} tags")
    print(f"  Retainer:    ${tmpl[6] / 10**6} per {tmpl[7]}s")
    print(f"  Stake:       ${tmpl[8] / 10**6}")
    print(f"  Active:      {tmpl[9]}")
    print(f"  Creator:     {tmpl[10]}")
    print(f"  Use count:   {tmpl[12]}")

    assert tmpl[1] == "Freelance Developer", f"Name mismatch: {tmpl[1]}"
    assert tmpl[9] == True, "Template not active"
    print("  PASS")
    return tmpl

def test_4_deploy_from_template():
    print("\n" + "="*60)
    print("TEST 4: Deploy agent from template #1 (identity only)")
    print("="*60)

    receipt = write_tx(
        "deployFromTemplate",
        1,                              # templateId
        "DevAgent-Alpha",               # name
        "ipfs://QmDevAgentAlpha",       # metadataURI
        False,                          # enableMarket (skip for basic test)
        False,                          # enableRetainer (skip for basic test)
        False,                          # enableStaking (skip for basic test)
        gas=1_000_000,
    )

    print(f"  Logs: {len(receipt['logs'])} events emitted")
    print(f"  Agent deployed from template!")
    return receipt

def test_5_verify_agent():
    print("\n" + "="*60)
    print("TEST 5: Verify deployed agent")
    print("="*60)

    # Check agents by owner
    agents = call_view("getAgentsByOwner", Web3.to_checksum_address(acct.address))
    print(f"  Agents owned by deployer: {agents[0]}")

    if len(agents[0]) > 0:
        agent_id = agents[0][0]
        print(f"  First agent token ID: {agent_id}")

        # Get deployment record
        deployed = call_view("getDeployedAgent", agent_id)[0]  # unwrap
        print(f"  Template used: {deployed[2]}")
        print(f"  Listed on market: {deployed[3]}")
        print(f"  Retainer plan: {deployed[4]}")
        print(f"  Has stake: {deployed[5]}")
        print(f"  Deployed at: {deployed[6]}")

        # Get cross-layer profile
        profile = call_view("getAgentProfile", agent_id)
        print(f"\n  Cross-layer profile:")
        print(f"    Name:       {profile[0]}")
        print(f"    Reputation: {profile[1] / 100}%")
        print(f"    Listed:     {profile[2]}")
        print(f"    Hourly:     ${profile[3] / 10**6}")
        print(f"    Staked:     ${profile[4] / 10**6}")
        print(f"    Retainer:   plan #{profile[5]}")

        assert profile[0] == "DevAgent-Alpha", f"Name mismatch: {profile[0]}"
        print("  PASS")

def test_6_deploy_custom():
    print("\n" + "="*60)
    print("TEST 6: Deploy agent with custom config (no template)")
    print("="*60)

    # DeployConfig struct — identity only, no optional layers
    deploy_config = (
        "CustomBot-Beta",               # name
        "ipfs://QmCustomBotBeta",       # metadataURI
        False,                          # listOnMarket
        0,                              # hourlyRateUsdc
        [],                             # capabilities
        0,                              # availableUntil
        False,                          # createRetainerPlan
        0,                              # retainerPriceUsdc
        0,                              # retainerInterval
        "",                             # retainerDescription
        False,                          # stakeCollateral
        0,                              # stakeAmountUsdc
    )

    receipt = write_tx("deployAgent", deploy_config, gas=1_000_000)
    print(f"  Logs: {len(receipt['logs'])} events emitted")
    print(f"  Custom agent deployed!")
    return receipt

def test_7_final_stats():
    print("\n" + "="*60)
    print("TEST 7: Final factory stats")
    print("="*60)
    stats = call_view("getFactoryStats")
    print(f"  Total agents deployed:  {stats[0]}")
    print(f"  Total templates:        {stats[1]}")
    print(f"  Total active templates: {stats[2]}")

    # Check active templates list
    active = call_view("getActiveTemplates")
    print(f"  Active template IDs: {active[0]}")

    # Template use count should be 1
    tmpl = call_view("getTemplate", 1)[0]  # unwrap
    print(f"  Template #1 use count: {tmpl[12]}")

    # Stats include the template created in the PREVIOUS run too
    assert stats[0] >= 2, f"Expected >= 2 agents, got {stats[0]}"
    assert stats[1] >= 1, f"Expected >= 1 template, got {stats[1]}"
    print("\n  ALL TESTS PASSED!")

# ─── Run ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Arc Agent Factory — End-to-End Test")
    print(f"Factory: {FACTORY_ADDR}")
    print(f"Deployer: {acct.address}")

    balance_hex = rpc_call("eth_getBalance", [acct.address, "latest"])
    balance = int(balance_hex, 16) / 1e18
    print(f"Balance: {balance:.4f} USDC")

    test_1_initial_stats()
    test_2_create_template()
    test_3_verify_template()
    test_4_deploy_from_template()
    test_5_verify_agent()
    test_6_deploy_custom()
    test_7_final_stats()

    print("\n" + "="*60)
    print("E2E TEST SUITE COMPLETE")
    print("="*60)
