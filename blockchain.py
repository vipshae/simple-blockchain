from time import time
import hashlib
import json


class Block(object):
    def __init__(self, index, transaction, proof, previous_hash=None):
        self.index = index
        self.timestamp = time()
        self.transaction = transaction
        self.proof = proof
        self.previous_hash = previous_hash

    def get_details(self):
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': [t.get_details() for t in self.transaction],
            'proof': self.proof,
            'previous_hash': self.previous_hash
        }


class Transaction(object):
    def __init__(self):
        self.sender = ""
        self.receiver = ""
        self.amount = ""

    def set_transaction(self, sender, receiver, amount):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount

    def get_details(self):
        return {
            'sender': self.sender,
            'receiver': self.receiver,
            'amount': self.amount
        }


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.currentTransactions = []
        # genesis block
        self.new_block(proof=100, previous_hash=1)

    def new_block(self, proof, previous_hash=None):
        """
        Creates new block in the blockchain
        :param proof: proof given by proof of work algo <int>
        :param previous_hash: Hash of previous block <str>
        :return: new Block <dict>
        """
        new_block = Block(index=len(self.chain)+1, transaction=self.currentTransactions, proof=proof,
                         previous_hash=previous_hash or self.hash(self.chain[-1]))

        self.chain.append(new_block)
        # reset current transactions after adding new block
        self.currentTransactions = []
        return new_block

    def new_transaction(self, sender, receiver, amount):
        """
        adds new transaction to go in the next mined block
        :param sender: Address of sender <str>
        :param receiver: Address of receiver <str>
        :param amount: amount transferred <int>
        :return: index of the block holding this transaction
        """
        new_transaction = Transaction()
        new_transaction.set_transaction(sender, receiver, amount)
        self.currentTransactions.append(new_transaction)
        return self.last_block.index + 1

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    def valid_proof(self, last_proof, current_proof):
        """
        Validates the Proof: Does hash(last_proof, current_proof) contain 4 leading zeroes?
        :param last_proof:  <int> Previous Proof
        :param current_proof: current proof
        :return: True if correct, False if not.
        """
        guess = f'{last_proof}{current_proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'


    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: <Block> Block
        :return: <str>
        """
        block_string = json.dumps(block.get_details(), sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # returns last block in chain
        return self.chain[-1]


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'get_details'):
            return obj.get_details()
        else:
            return json.JSONEncoder.default(self, obj)


#sample block
block = {
    'index': 1,
    'timestamp': 1506057125.900785,
    'transactions': [
        {
            'sender': "8527147fe1f5426f9dd545de4b27ee00",
            'recipient': "a77f5cdfa2934df3954a5c7c7da5df1f",
            'amount': 5,
        }
    ],
    'proof': 324984774000,
    'previous_hash': "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
}
