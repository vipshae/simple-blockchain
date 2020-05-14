from time import time
import hashlib
import json
from urllib.parse import urlparse
import requests


class Block(object):
    def __init__(self, index, timestamp, transaction, proof, previous_hash=None):
        self.index = index
        self.timestamp = timestamp or time()
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
    # difficulty of PoW algorithm
    difficulty = 4

    def __init__(self):
        self.chain = []
        self.currentTransactions = []
        self.nodes = set()
        self._chain_len = len(self.chain)
        # genesis block
        self.create_genesis_block()

    def create_genesis_block(self):
        """
        A function to generate genesis block and appends it to
        the chain.
        """
        self.new_block(proof=100, previous_hash=1)

    def __len__(self):
        return self._chain_len

    def new_block(self, index=None, timestamp=None, transaction=None, proof=None, previous_hash=None):
        """
        Creates new block in the blockchain
        :param timestamp:
        :param index:
        :param transaction:
        :param proof: proof given by proof of work algo <int>
        :param previous_hash: Hash of previous block <str>
        :return: new Block <dict>
        """
        new_block = Block(index=index or len(self.chain) + 1, timestamp=timestamp,
                          transaction=transaction or self.currentTransactions,
                          proof=proof, previous_hash=previous_hash or self.hash(self.chain[-1]))

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
         - Find a number/nonce p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """
        proof = 0
        while self.is_valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    def is_valid_proof(self, last_proof, current_proof):
        """
        Validates the Proof: Does hash(last_proof, current_proof) contain 4 leading zeroes?
        :param last_proof:  <int> Previous Proof
        :param current_proof: current proof
        :return: True if correct, False if not.
        """
        guess = f'{last_proof}{current_proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:Blockchain.difficulty] == '0' * Blockchain.difficulty

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """
        self.nodes.add(urlparse(address).netloc)

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")

            # check if hash of block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # check if proof of work of block is correct
            if not self.is_valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """
        neighbours = self.nodes
        new_chain = None
        max_len = len(self.chain)
        length = 0
        chain = None

        # verify chains from all the nodes in the network
        for node in neighbours:
            if node is not None or node != '':
                resp = requests.get(f'http://{node}/chain')
            else:
                continue
            if resp.status_code == 200:
                length = resp.json()['length']
                chain = resp.json()['chain']

            # check if len of neighbour chain is longer than self length and its chain is valid
            if length >= max_len and self.valid_chain(chain):
                new_chain = chain
                max_len = length

        # replace our chain if new chain was found
        if new_chain:
            self.chain = new_chain
            return True

        return False

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


# sample block
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
