#!/usr/bin/env python3
"""
Full stack redeploy — all layer contracts pointing to AgentIdentity V2.

Deploy order:
  1. AgentJob(identityV2, USDC)
  2. AgentOrchestrator(identityV2, USDC)
  3. AgentRetainer(identityV2, USDC)
  4. AgentStaking(identityV2, USDC)
  5. AgentMarket(identityV2, newJob, USDC)
  6. AgentDAO(identityV2, USDC)

Post-deploy config:
  - Identity V2: setTrustedUpdater(Job, true), setTrustedUpdater(Orchestrator, true)
  - Staking: setAuthorizedSlasher(Job, true), setAuthorizedSlasher(Orchestrator, true)

Then redeploy Factory pointing to all new addresses.
"""

import json, os, sys, time, requests
import solcx
from eth_account import Account
from web3 import Web3

# ─── Config ────────────────────────────────────────────────────────────────

ARC_RPC    = "https://rpc.testnet.arc.network"
CHAIN_ID   = 5042002
SOLC_VER   = "0.8.24"
USDC_ADDR  = "0x3600000000000000000000000000000000000000"
IDENTITY_V2 = "0x0bf50994245ab3297ed95665d62192977930fabb"

PRIVATE_KEY = os.environ.get("DEPLOYER_PRIVATE_KEY")
assert PRIVATE_KEY, "DEPLOYER_PRIVATE_KEY not set"

MAX_FEE  = Web3.to_wei(25, "gwei")
PRIORITY = Web3.to_wei(2,  "gwei")

proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
PROXIES = {"https": proxy, "http": proxy} if proxy else {}

# GitHub repos
REPOS = {
    "job":          ("sethoshi18", "arc-agent-payments"),
    "market":       ("sethoshi18", "arc-agent-market"),
    "orchestrator": ("sethoshi18", "arc-agent-orchestrator"),
    "retainer":     ("sethoshi18", "arc-agent-retainer"),
    "staking":      ("sethoshi18", "arc-agent-staking"),
    "dao":          ("sethoshi18", "arc-agent-dao"),
}

# Contract file paths within each repo
CONTRACT_FILES = {
    "job":          ["contracts/AgentJob.sol", "contracts/interfaces/IERC8183.sol", "contracts/interfaces/IERC8004.sol"],
    "market":       ["contracts/AgentMarket.sol", "contracts/interfaces/IAgentMarket.sol"],
    "orchestrator": ["contracts/AgentOrchestrator.sol"],
    "retainer":     ["contracts/AgentRetainer.sol"],
    "staking":      ["contracts/AgentStaking.sol"],
    "dao":          ["contracts/AgentDAO.sol"],
}

# Contract names for compilation key lookup
CONTRACT_NAMES = {
    "job": "AgentJob",
    "market": "AgentMarket",
    "orchestrator": "AgentOrchestrator",
    "retainer": "AgentRetainer",
    "staking": "AgentStaking",
    "dao": "AgentDAO",
}

# ─── Helpers ───────────────────────────────────────────────────────────────

def rpc(method, params=None):
    resp = requests.post(ARC_RPC, json={"jsonrpc":"2.0","id":1,"method":method,"params":params or []},
                         proxies=PROXIES, timeout=30, verify=False)
    data = resp.json()
    if "error" in data:
        raise Exception(f"RPC error: {data['error']}")
    return data["result"]

def wait_receipt(tx_hash, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        result = rpc("eth_getTransactionReceipt", [tx_hash])
        if result is not None:
            if int(result["status"], 16) != 1:
                raise Exception(f"TX REVERTED: {tx_hash}")
            return result
        time.sleep(3)
    raise Exception(f"Timeout: {tx_hash}")

def deploy(abi, bytecode, constructor_args, label):
    acct = Account.from_key(PRIVATE_KEY)
    nonce = int(rpc("eth_getTransactionCount", [acct.address, "latest"]), 16)
    w3 = Web3()
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = contract.constructor(*constructor_args).build_transaction({
        "from": acct.address, "nonce": nonce, "gas": 6_000_000,
        "maxFeePerGas": MAX_FEE, "maxPriorityFeePerGas": PRIORITY,
        "chainId": CHAIN_ID, "value": 0,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = rpc("eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])
    print(f"  {label} TX: {tx_hash}")
    receipt = wait_receipt(tx_hash)
    addr = receipt["contractAddress"]
    gas = int(receipt["gasUsed"], 16)
    print(f"  {label}: {addr} (gas: {gas:,})")
    return addr, abi

def send_config_tx(to, data, label):
    acct = Account.from_key(PRIVATE_KEY)
    nonce = int(rpc("eth_getTransactionCount", [acct.address, "latest"]), 16)
    tx = {
        "from": acct.address, "to": Web3.to_checksum_address(to),
        "data": data, "nonce": nonce, "gas": 200_000,
        "maxFeePerGas": MAX_FEE, "maxPriorityFeePerGas": PRIORITY,
        "chainId": CHAIN_ID, "type": 2, "value": 0,
    }
    signed = acct.sign_transaction(tx)
    tx_hash = rpc("eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])
    wait_receipt(tx_hash)
    print(f"  {label}: OK")

def fetch_github_file(owner, repo, path):
    """Fetch raw file content from GitHub."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"
    resp = requests.get(url, proxies=PROXIES, timeout=15, verify=False)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch {url}: {resp.status_code}")
    return resp.text

# ─── Step 1: Fetch all contracts from GitHub ───────────────────────────────

print("=" * 60)
print("STEP 1: Fetching contracts from GitHub")
print("=" * 60)

base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources")
os.makedirs(base_dir, exist_ok=True)

for layer, (owner, repo) in REPOS.items():
    layer_dir = os.path.join(base_dir, layer, "contracts")
    os.makedirs(os.path.join(layer_dir, "interfaces"), exist_ok=True)

    for filepath in CONTRACT_FILES[layer]:
        content = fetch_github_file(owner, repo, filepath)
        local_path = os.path.join(base_dir, layer, filepath)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w") as f:
            f.write(content)
        print(f"  {layer}/{filepath} ({len(content)} bytes)")

print(f"  All sources fetched.\n")

# ─── Step 2: Compile all contracts ─────────────────────────────────────────

print("=" * 60)
print("STEP 2: Compiling contracts")
print("=" * 60)

solcx.install_solc(SOLC_VER)

compiled_contracts = {}
for layer in CONTRACT_NAMES:
    name = CONTRACT_NAMES[layer]
    main_file = CONTRACT_FILES[layer][0]
    local_main = os.path.join(base_dir, layer, main_file)
    contracts_dir = os.path.join(base_dir, layer, "contracts")

    all_files = [os.path.join(base_dir, layer, f) for f in CONTRACT_FILES[layer]]

    try:
        compiled = solcx.compile_files(
            all_files,
            output_values=["abi", "bin"],
            solc_version=SOLC_VER,
            optimize=True, optimize_runs=200,
            base_path=contracts_dir,
            allow_paths=[contracts_dir, os.path.join(contracts_dir, "interfaces")],
        )
        # Find the right key
        key = None
        for k in compiled:
            if k.endswith(f":{name}"):
                key = k
                break
        if not key:
            # Try partial match
            for k in compiled:
                if name in k and "interface" not in k.lower():
                    key = k
                    break

        if not key:
            print(f"  WARNING: {name} not found in compiled output. Keys: {list(compiled.keys())}")
            continue

        abi = compiled[key]["abi"]
        bytecode = compiled[key]["bin"]
        compiled_contracts[layer] = {"abi": abi, "bin": "0x" + bytecode, "name": name}
        print(f"  {name}: {len(abi)} ABI entries, {len(bytecode)//2} bytes")
    except Exception as e:
        print(f"  ERROR compiling {name}: {e}")

print(f"  Compiled {len(compiled_contracts)}/{len(CONTRACT_NAMES)} contracts.\n")

# ─── Step 3: Deploy in order ───────────────────────────────────────────────

print("=" * 60)
print("STEP 3: Deploying contracts (Identity V2: " + IDENTITY_V2 + ")")
print("=" * 60)

acct = Account.from_key(PRIVATE_KEY)
ID = Web3.to_checksum_address(IDENTITY_V2)
USDC = Web3.to_checksum_address(USDC_ADDR)

addresses = {"identity": IDENTITY_V2}

# 1. AgentJob(identityV2, USDC)
if "job" in compiled_contracts:
    c = compiled_contracts["job"]
    addr, _ = deploy(c["abi"], c["bin"], [ID, USDC], "AgentJob")
    addresses["job"] = addr

# 2. AgentOrchestrator(identityV2, USDC)
if "orchestrator" in compiled_contracts:
    c = compiled_contracts["orchestrator"]
    addr, _ = deploy(c["abi"], c["bin"], [ID, USDC], "AgentOrchestrator")
    addresses["orchestrator"] = addr

# 3. AgentRetainer(identityV2, USDC)
if "retainer" in compiled_contracts:
    c = compiled_contracts["retainer"]
    addr, _ = deploy(c["abi"], c["bin"], [ID, USDC], "AgentRetainer")
    addresses["retainer"] = addr

# 4. AgentStaking(identityV2, USDC)
if "staking" in compiled_contracts:
    c = compiled_contracts["staking"]
    addr, _ = deploy(c["abi"], c["bin"], [ID, USDC], "AgentStaking")
    addresses["staking"] = addr

# 5. AgentMarket(identityV2, newJob, USDC) — needs Job address
if "market" in compiled_contracts and "job" in addresses:
    c = compiled_contracts["market"]
    addr, _ = deploy(c["abi"], c["bin"], [ID, Web3.to_checksum_address(addresses["job"]), USDC], "AgentMarket")
    addresses["market"] = addr

# 6. AgentDAO(identityV2, USDC)
if "dao" in compiled_contracts:
    c = compiled_contracts["dao"]
    addr, _ = deploy(c["abi"], c["bin"], [ID, USDC], "AgentDAO")
    addresses["dao"] = addr

print(f"\n  All {len(addresses)-1} layer contracts deployed.\n")

# ─── Step 4: Configure permissions ────────────────────────────────────────

print("=" * 60)
print("STEP 4: Configuring permissions")
print("=" * 60)

w3 = Web3()

# Identity V2: setTrustedUpdater(job, true) + setTrustedUpdater(orchestrator, true)
set_trusted_abi = [{"type":"function","name":"setTrustedUpdater","inputs":[{"name":"updater","type":"address"},{"name":"trusted","type":"bool"}],"outputs":[],"stateMutability":"nonpayable"}]
id_contract = w3.eth.contract(address=ID, abi=set_trusted_abi)

if "job" in addresses:
    data = id_contract.get_function_by_name("setTrustedUpdater")(Web3.to_checksum_address(addresses["job"]), True)._encode_transaction_data()
    send_config_tx(IDENTITY_V2, data, "Identity: trust Job")

if "orchestrator" in addresses:
    data = id_contract.get_function_by_name("setTrustedUpdater")(Web3.to_checksum_address(addresses["orchestrator"]), True)._encode_transaction_data()
    send_config_tx(IDENTITY_V2, data, "Identity: trust Orchestrator")

# Staking: setAuthorizedSlasher(job, true) + setAuthorizedSlasher(orchestrator, true)
if "staking" in addresses:
    set_slasher_abi = [{"type":"function","name":"setAuthorizedSlasher","inputs":[{"name":"slasher","type":"address"},{"name":"authorized","type":"bool"}],"outputs":[],"stateMutability":"nonpayable"}]
    staking_contract = w3.eth.contract(address=Web3.to_checksum_address(addresses["staking"]), abi=set_slasher_abi)

    if "job" in addresses:
        data = staking_contract.get_function_by_name("setAuthorizedSlasher")(Web3.to_checksum_address(addresses["job"]), True)._encode_transaction_data()
        send_config_tx(addresses["staking"], data, "Staking: authorize Job slasher")

    if "orchestrator" in addresses:
        data = staking_contract.get_function_by_name("setAuthorizedSlasher")(Web3.to_checksum_address(addresses["orchestrator"]), True)._encode_transaction_data()
        send_config_tx(addresses["staking"], data, "Staking: authorize Orchestrator slasher")

print(f"\n  Permissions configured.\n")

# ─── Step 5: Redeploy AgentFactory ─────────────────────────────────────────

print("=" * 60)
print("STEP 5: Redeploying AgentFactory")
print("=" * 60)

factory_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "contracts")
factory_path = os.path.join(factory_dir, "AgentFactory.sol")
iface_path = os.path.join(factory_dir, "interfaces", "IAgentFactory.sol")

compiled_f = solcx.compile_files(
    [factory_path, iface_path],
    output_values=["abi", "bin"],
    solc_version=SOLC_VER,
    optimize=True, optimize_runs=200,
    base_path=factory_dir,
    allow_paths=[factory_dir],
)
f_key = [k for k in compiled_f if k.endswith(":AgentFactory")][0]
f_abi = compiled_f[f_key]["abi"]
f_bin = "0x" + compiled_f[f_key]["bin"]

factory_addr, _ = deploy(
    f_abi, f_bin,
    [
        ID,
        Web3.to_checksum_address(addresses.get("market", "0x0000000000000000000000000000000000000000")),
        Web3.to_checksum_address(addresses.get("retainer", "0x0000000000000000000000000000000000000000")),
        Web3.to_checksum_address(addresses.get("staking", "0x0000000000000000000000000000000000000000")),
        USDC,
    ],
    "AgentFactory"
)
addresses["factory"] = factory_addr

# ─── Summary ───────────────────────────────────────────────────────────────

print(f"\n{'='*60}")
print("FULL STACK REDEPLOY COMPLETE")
print(f"{'='*60}")
for layer, addr in addresses.items():
    label = layer.capitalize().ljust(15)
    print(f"  {label}: {addr}")
print(f"\n  Explorer: https://testnet.arcscan.app/address/{factory_addr}")

# Save
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deployment_v3.json")
with open(out_path, "w") as f:
    json.dump(addresses, f, indent=2)
print(f"\n  Saved to deployment_v3.json")

# Final balance
balance = int(rpc("eth_getBalance", [acct.address, "latest"]), 16) / 1e18
print(f"  Deployer balance remaining: {balance:.4f} USDC")
