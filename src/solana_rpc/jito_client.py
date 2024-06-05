from random import sample

from retry import retry
from solana.exceptions import SolanaRpcException
from solana.transaction import Transaction
from solders.hash import Hash
from solders.instruction import Instruction
from solders.pubkey import Pubkey
from solders.rpc.responses import SendTransactionResp
from solders.system_program import TransferParams, transfer

from src.constants import JITO_RPC_ENDPOINT, JITO_TIP_ACCOUNTS, JITO_TIP_IN_SOLAMI
from src.solana_rpc.base_client import SolanaBaseClient


class SolanaJitoClient(SolanaBaseClient):
    def __init__(self, private_key: str) -> None:
        url = JITO_RPC_ENDPOINT
        super().__init__(url=url, private_key=private_key)

    @retry(exceptions=(SolanaRpcException,), tries=4, delay=3, backoff=2)
    def execute_transaction(
        self,
        tx_buffer: list[int],
        recent_blockhash: Hash | None,
    ) -> SendTransactionResp:
        assert recent_blockhash, "Recent blockhash is required for Jito transactions"

        transaction = Transaction.deserialize(bytes(tx_buffer))
        tip_instruction = self.get_tip_instruction(
            tip_in_solami=int(JITO_TIP_IN_SOLAMI)
        )
        transaction.add(tip_instruction)
        response = self.client.send_transaction(
            transaction, self.keypair, recent_blockhash=recent_blockhash
        )
        return response

    def get_tip_instruction(self, tip_in_solami: int) -> Instruction:
        tip_account = sample(JITO_TIP_ACCOUNTS, 1)[0]
        tip_account_pubkey = Pubkey.from_string(tip_account)
        tip_instruction = transfer(
            TransferParams(
                from_pubkey=self.keypair.pubkey(),
                to_pubkey=tip_account_pubkey,
                lamports=tip_in_solami,
            )
        )
        return tip_instruction
