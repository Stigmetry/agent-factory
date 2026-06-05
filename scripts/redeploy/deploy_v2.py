#!/usr/bin/env python3
"""
Redeploy AgentIdentity V2 (with transferAgent) + AgentFactory V2.

Steps:
  1. Compile AgentIdentityV2.sol
  2. Deploy AgentIdentityV2
  3. Set trustedUpdaters on V2 (AgentJob + AgentOrchestrator)
  4. Recompile AgentFactory with updated interface
  5. Deploy AgentFactory V2 (pointing to new identity + existing layers)
"""

import json
import os
import sys
import time
import requests
import solcx
from eth_account import Account
from web3 import Web3

ARC_RPC    = "https://rpc.testnet.arc.network"
CHAIN_ID   = 5042002
SOLC_VER   = "0.8.24"

# Existing layer addresses (unchanged)
JOB_ADDR           = "0xD698d15F776279c0213444a779941e8E0Cbe5094"
MARKET_ADDR        = "0x6BAf93EB026b7BC3db651065302D1934Ad577ec1"
ORCHESTRATOR_ADDR  = "0xbA99f039b7892d9F546253444c95EDea822471b0"
RETAINER_ADDR      = "0x5C80B95Ac3c2eE748F427aBB15Ad5d3E94fcD8D6"
STAKING_ADDR       = "0x0107BD44E269888F12dCc32E9bc03E79Ca7Be770"
DAO_ADDR           = "0x213157853e67BC17F4b69B8F3f5b0fe14C64fCf7"
USDC_ADDR          = "0x3600000000000000000000000000000000000000"

PRIVATE_KEY = os.environ.get("DEPLOYER_PRIVATE_KEY")
assert PRIVATE_KEY, "DEPLOYER_PRIVATE_KEY not set"

MAX_FEE  = Web3.to_wei(25, "gwei")
PRIORITY = Web3.to_wei(2,  "gwei")

# ─── Helpers ───────────────────────────────────────────────────────────────

def get_proxy():
    return os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

def rpc(method, params=None):
    proxy = get_proxy()
    proxies = {"https": proxy, "http": proxy} if proxy else {}
    resp = requests.post(ARC_RPC, json={"jsonrpc":"2.0","id":1,"method":method,"params":params or []},
                         proxies=proxies, timeout=30)
    data = resp.json()
    if "error" in data:
        raise Exception(f"RPC error: {data['error']}")
    return data["result"]

def wait(tx_hash, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        result = rpc("eth_getTransactionReceipt", [tx_hash])
        if result is not None:
            if int(result["status"], 16) != 1:
                raise Exception(f"TX REVERTED: {tx_hash}")
            return result
        time.sleep(3)
    raise Exception(f"Timeout: {tx_hash}")

def deploy_contract(abi, bytecode, constructor_args, label):
    acct = Account.from_key(PRIVATE_KEY)
    nonce = int(rpc("eth_getTransactionCount", [acct.address, "latest"]), 16)

    w3 = Web3()
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = contract.constructor(*constructor_args).build_transaction({
        "from": acct.address, "nonce": nonce, "gas": 5_000_000,
        "maxFeePerGas": MAX_FEE, "maxPriorityFeePerGas": PRIORITY,
        "chainId": CHAIN_ID, "value": 0,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = rpc("eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])
    print(f"  {label} TX: {tx_hash}")
    receipt = wait(tx_hash)
    addr = receipt["contractAddress"]
    gas = int(receipt["gasUsed"], 16)
    print(f"  {label} deployed: {addr} (gas: {gas:,})")
    return addr, abi

def send_tx(to, data):
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
    receipt = wait(tx_hash)
    return tx_hash

# ─── Step 1: Compile AgentIdentityV2 ──────────────────────────────────────

print("\n=== Step 1: Compile AgentIdentityV2 ===")
solcx.install_solc(SOLC_VER)

script_dir = os.path.dirname(os.path.abspath(__file__))
identity_path = os.path.join(script_dir, "AgentIdentityV2.sol")

compiled_id = solcx.compile_files(
    [identity_path],
    output_values=["abi", "bin"],
    solc_version=SOLC_VER,
    optimize=True, optimize_runs=200,
)
id_key = [k for k in compiled_id if "AgentIdentityV2" in k and "IERC8004" not in k][0]
id_abi = compiled_id[id_key]["abi"]
id_bin = compiled_id[id_key]["bin"]
print(f"  Compiled: {len(id_abi)} ABI entries, {len(id_bin)//2} bytes")

# ─── Step 2: Deploy AgentIdentityV2 ───────────────────────────────────────

print("\n=== Step 2: Deploy AgentIdentityV2 ===")
new_identity_addr, _ = deploy_contract(id_abi, "0x" + id_bin, [], "AgentIdentityV2")

# ─── Step 3: Set trusted updaters ─────────────────────────────────────────

print("\n=== Step 3: Set trusted updaters on new identity ===")
w3 = Web3()
id_contract = w3.eth.contract(address=Web3.to_checksum_address(new_identity_addr), abi=id_abi)

# AgentJob as trusted updater
fn = id_contract.get_function_by_name("setTrustedUpdater")
data = fn(Web3.to_checksum_address(JOB_ADDR), True)._encode_transaction_data()
tx1 = send_tx(new_identity_addr, data)
print(f"  Trusted: AgentJob {JOB_ADDR}")

# AgentOrchestrator as trusted updater
data2 = fn(Web3.to_checksum_address(ORCHESTRATOR_ADDR), True)._encode_transaction_data()
tx2 = send_tx(new_identity_addr, data2)
print(f"  Trusted: AgentOrchestrator {ORCHESTRATOR_ADDR}")

# ─── Step 4: Recompile AgentFactory ───────────────────────────────────────

print("\n=== Step 4: Recompile AgentFactory ===")
contracts_dir = os.path.join(script_dir, "..", "..", "contracts")
factory_path = os.path.join(contracts_dir, "AgentFactory.sol")
iface_path = os.path.join(contracts_dir, "interfaces", "IAgentFactory.sol")

compiled_f = solcx.compile_files(
    [factory_path, iface_path],
    output_values=["abi", "bin"],
    solc_version=SOLC_VER,
    optimize=True, optimize_runs=200,
    base_path=contracts_dir,
    allow_paths=[contracts_dir],
)
f_key = [k for k in compiled_f if k.endswith(":AgentFactory")][0]
f_abi = compiled_f[f_key]["abi"]
f_bin = compiled_f[f_key]["bin"]
print(f"  Compiled: {len(f_abi)} ABI entries, {len(f_bin)//2} bytes")

# ─── Step 5: Deploy AgentFactory V2 ──────────────────────────────────────

print("\n=== Step 5: Deploy AgentFactory V2 ===")
new_factory_addr, _ = deploy_contract(
    f_abi, "0x" + f_bin,
    [
        Web3.to_checksum_address(new_identity_addr),
        Web3.to_checksum_address(MARKET_ADDR),
        Web3.to_checksum_address(RETAINER_ADDR),
        Web3.to_checksum_address(STAKING_ADDR),
        Web3.to_checksum_address(USDC_ADDR),
    ],
    "AgentFactoryV2"
)

# ─── Summary ──────────────────────────────────────────────────────────────

print(f"\n{'='*60}")
print(f"REDEPLOY COMPLETE")
print(f"  AgentIdentityV2: {new_identity_addr}")
print(f"  AgentFactoryV2:  {new_factory_addr}")
print(f"  Explorer: https://testnet.arcscan.app/address/{new_factory_addr}")
print(f"{'='*60}")

# Save deployment info
deployment = {
    "identityV2": new_identity_addr,
    "factoryV2": new_factory_addr,
    "identityV2_abi": id_abi,
    "factoryV2_abi": f_abi,
}
out_path = os.path.join(script_dir, "..", "..", "deployment_v2.json")
with open(out_path, "w") as f:
    json.dump(deployment, f, indent=2)
print(f"\nSaved to deployment_v2.json")
