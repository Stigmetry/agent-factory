#!/usr/bin/env python3
"""
Deploy AgentFactory (Layer 8) to Arc Testnet.

Requires:
  pip install py-solc-x web3 eth-account requests

Layer contract addresses (already deployed on Arc Testnet, Chain ID 5042002):
  Layer 1 — AgentIdentity:    0x5Bef356f89425823FC7eebB3A6ED1A678F3b8233
  Layer 3 — AgentMarket:      0x6BAf93EB026b7BC3db651065302D1934Ad577ec1
  Layer 5 — AgentRetainer:    0x5C80B95Ac3c2eE748F427aBB15Ad5d3E94fcD8D6
  Layer 6 — AgentStaking:     0x0107BD44E269888F12dCc32E9bc03E79Ca7Be770
  USDC:                       0x3600000000000000000000000000000000000000
"""

import json
import os
import sys
import time

import requests
import solcx
from eth_account import Account
from web3 import Web3

# ─── Config ────────────────────────────────────────────────────────────────

ARC_RPC       = "https://rpc.testnet.arc.network"
CHAIN_ID      = 5042002
SOLC_VERSION  = "0.8.24"

# Layer contract addresses
IDENTITY_ADDR  = "0x5Bef356f89425823FC7eebB3A6ED1A678F3b8233"
MARKET_ADDR    = "0x6BAf93EB026b7BC3db651065302D1934Ad577ec1"
RETAINER_ADDR  = "0x5C80B95Ac3c2eE748F427aBB15Ad5d3E94fcD8D6"
STAKING_ADDR   = "0x0107BD44E269888F12dCc32E9bc03E79Ca7Be770"
USDC_ADDR      = "0x3600000000000000000000000000000000000000"

# Deployer wallet
PRIVATE_KEY = os.environ.get("DEPLOYER_PRIVATE_KEY")

# Gas settings (Arc testnet min base fee ~20 gwei)
MAX_FEE_PER_GAS       = Web3.to_wei(25, "gwei")
MAX_PRIORITY_FEE      = Web3.to_wei(2,  "gwei")

# ─── Helpers ───────────────────────────────────────────────────────────────

def get_proxy():
    return os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

def rpc_call(method, params=None):
    proxy = get_proxy()
    proxies = {"https": proxy, "http": proxy} if proxy else {}
    resp = requests.post(
        ARC_RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []},
        proxies=proxies,
        timeout=30,
    )
    data = resp.json()
    if "error" in data:
        raise Exception(f"RPC error: {data['error']}")
    return data["result"]


def wait_for_receipt(tx_hash, timeout=120):
    """Poll for transaction receipt."""
    start = time.time()
    while time.time() - start < timeout:
        result = rpc_call("eth_getTransactionReceipt", [tx_hash])
        if result is not None:
            status = int(result["status"], 16)
            if status != 1:
                raise Exception(f"Transaction reverted: {tx_hash}")
            return result
        time.sleep(3)
    raise Exception(f"Timeout waiting for receipt: {tx_hash}")


def compile_contracts():
    """Compile AgentFactory with py-solc-x."""
    print("Installing solc", SOLC_VERSION, "...")
    solcx.install_solc(SOLC_VERSION)

    contracts_dir = os.path.join(os.path.dirname(__file__), "..", "contracts")
    factory_path = os.path.join(contracts_dir, "AgentFactory.sol")
    interface_path = os.path.join(contracts_dir, "interfaces", "IAgentFactory.sol")

    print("Compiling AgentFactory.sol ...")
    compiled = solcx.compile_files(
        [factory_path, interface_path],
        output_values=["abi", "bin"],
        solc_version=SOLC_VERSION,
        optimize=True,
        optimize_runs=200,
        import_remappings=[
            f"./interfaces/={os.path.join(contracts_dir, 'interfaces')}/"
        ],
        base_path=contracts_dir,
        allow_paths=[contracts_dir],
    )

    # Find the AgentFactory contract in compiled output
    factory_key = None
    for key in compiled:
        if "AgentFactory" in key and "IAgentFactory" not in key and "IERC" not in key:
            factory_key = key
            break

    if not factory_key:
        print("Available keys:", list(compiled.keys()))
        raise Exception("AgentFactory not found in compiled output")

    abi      = compiled[factory_key]["abi"]
    bytecode = compiled[factory_key]["bin"]

    print(f"Compiled: {factory_key}")
    print(f"  ABI entries: {len(abi)}")
    print(f"  Bytecode size: {len(bytecode) // 2} bytes")

    return abi, bytecode


def deploy(abi, bytecode):
    """Deploy AgentFactory to Arc Testnet."""
    if not PRIVATE_KEY:
        raise Exception("DEPLOYER_PRIVATE_KEY not set")

    acct = Account.from_key(PRIVATE_KEY)
    print(f"\nDeployer: {acct.address}")

    # Check balance
    balance_hex = rpc_call("eth_getBalance", [acct.address, "latest"])
    balance_wei = int(balance_hex, 16)
    balance_usdc = balance_wei / 1e18  # Native USDC uses 18 decimals
    print(f"Balance: {balance_usdc:.4f} USDC")

    if balance_usdc < 0.1:
        raise Exception("Insufficient balance for deployment gas")

    # Get nonce
    nonce_hex = rpc_call("eth_getTransactionCount", [acct.address, "latest"])
    nonce = int(nonce_hex, 16)
    print(f"Nonce: {nonce}")

    # Build constructor args
    w3 = Web3()
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    constructor_data = contract.constructor(
        Web3.to_checksum_address(IDENTITY_ADDR),
        Web3.to_checksum_address(MARKET_ADDR),
        Web3.to_checksum_address(RETAINER_ADDR),
        Web3.to_checksum_address(STAKING_ADDR),
        Web3.to_checksum_address(USDC_ADDR),
    ).build_transaction({
        "from":                 acct.address,
        "nonce":                nonce,
        "gas":                  5_000_000,
        "maxFeePerGas":         MAX_FEE_PER_GAS,
        "maxPriorityFeePerGas": MAX_PRIORITY_FEE,
        "chainId":              CHAIN_ID,
        "value":                0,
    })

    # Sign and send
    signed = acct.sign_transaction(constructor_data)
    raw_hex = "0x" + signed.raw_transaction.hex()

    print("\nSending deployment transaction ...")
    tx_hash = rpc_call("eth_sendRawTransaction", [raw_hex])
    print(f"TX hash: {tx_hash}")

    # Wait for receipt
    print("Waiting for confirmation ...")
    receipt = wait_for_receipt(tx_hash)
    contract_address = receipt["contractAddress"]

    print(f"\n{'='*60}")
    print(f"AgentFactory deployed!")
    print(f"  Address:  {contract_address}")
    print(f"  TX hash:  {tx_hash}")
    print(f"  Block:    {int(receipt['blockNumber'], 16)}")
    print(f"  Gas used: {int(receipt['gasUsed'], 16)}")
    print(f"  Explorer: https://testnet.arcscan.app/address/{contract_address}")
    print(f"{'='*60}")

    # Save deployment info
    deployment = {
        "contract": "AgentFactory",
        "address": contract_address,
        "txHash": tx_hash,
        "block": int(receipt["blockNumber"], 16),
        "gasUsed": int(receipt["gasUsed"], 16),
        "deployer": acct.address,
        "chainId": CHAIN_ID,
        "constructorArgs": {
            "identity": IDENTITY_ADDR,
            "market":   MARKET_ADDR,
            "retainer": RETAINER_ADDR,
            "staking":  STAKING_ADDR,
            "usdc":     USDC_ADDR,
        },
        "abi": abi,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "deployment.json")
    with open(out_path, "w") as f:
        json.dump(deployment, f, indent=2)
    print(f"\nDeployment info saved to deployment.json")

    return contract_address


# ─── Main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    abi, bytecode = compile_contracts()

    if "--compile-only" in sys.argv:
        # Save ABI for SDK use
        out_path = os.path.join(os.path.dirname(__file__), "..", "abi.json")
        with open(out_path, "w") as f:
            json.dump(abi, f, indent=2)
        print(f"\nABI saved to abi.json")
        sys.exit(0)

    deploy(abi, bytecode)
