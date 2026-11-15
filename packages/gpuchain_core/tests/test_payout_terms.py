import copy
import unittest
from decimal import Decimal

from eth_account import Account
from gpuchain_core.payout_terms import job_binding, new_job_ids, provider_quote, validate_terms, workload_hash


class SignedTerms(unittest.TestCase):
    def setUp(self):
        self.client_key, self.provider_key = "0x" + "8" * 64, "0x" + "c" * 64
        self.client = Account.from_key(self.client_key).address.lower()
        self.wallet = Account.from_key(self.provider_key).address.lower()
        self.job, self.onchain = new_job_ids(self.client)
        self.contract, self.chain = "0x" + "1" * 40, 31337
        quote = provider_quote(job_id=self.job, onchain_id=self.onchain, chain_id=self.chain, contract=self.contract, provider_id="provider", rate="0.001", workload=workload_hash({}), key=self.provider_key)
        self.spec = {"provider_terms": [{"provider_id": "provider", "wallet": self.wallet, "price_per_step": "0.001", "quote": quote}]}
        self.policy = {"metric": "accuracy"}
        self.binding = job_binding(job_id=self.job, onchain_id=self.onchain, chain_id=self.chain, contract=self.contract, spec=self.spec, policy=self.policy, budget="5", key=self.client_key)

    def check(self):
        validate_terms(job_id=self.job, client=self.client, binding=self.binding, spec=self.spec, policy=self.policy, budget=Decimal("5"), chain_id=self.chain, contract=self.contract)

    def test_signed_job_and_provider_quote(self):
        self.check()

    def test_rejects_client_provider_and_domain_tampering(self):
        for change in ("client", "price", "quote", "contract", "budget", "duplicate"):
            with self.subTest(change=change):
                self.setUp()
                if change == "client": self.client = "0x" + "2" * 40
                if change == "price": self.spec["provider_terms"][0]["price_per_step"] = "0.5"
                if change == "quote":
                    self.spec["provider_terms"][0]["quote"]["signature"] = "0x00"
                    self.binding = job_binding(job_id=self.job, onchain_id=self.onchain, chain_id=self.chain, contract=self.contract, spec=self.spec, policy=self.policy, budget="5", key=self.client_key)
                if change == "contract": self.contract = "0x" + "2" * 40
                if change == "budget": self.binding["budget"] = "9"
                if change == "duplicate":
                    self.spec["provider_terms"].append(copy.deepcopy(self.spec["provider_terms"][0]))
                    self.binding = job_binding(job_id=self.job, onchain_id=self.onchain, chain_id=self.chain, contract=self.contract, spec=self.spec, policy=self.policy, budget="5", key=self.client_key)
                with self.assertRaises(ValueError): self.check()

    def test_rejects_a_budget_that_is_negative_or_finer_than_a_micro_usdc(self):
        for budget in ("-5", "0", "5.0000001", "NaN", "Infinity"):
            with self.subTest(budget=budget):
                self.binding = job_binding(job_id=self.job, onchain_id=self.onchain, chain_id=self.chain, contract=self.contract, spec=self.spec, policy=self.policy, budget=budget, key=self.client_key)
                with self.assertRaises(ValueError):
                    validate_terms(job_id=self.job, client=self.client, binding=self.binding, spec=self.spec, policy=self.policy, budget=Decimal(budget), chain_id=self.chain, contract=self.contract)
