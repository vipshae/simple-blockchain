from flask import Flask, request
from uuid import uuid4
from blockchain import Blockchain, ComplexEncoder
import json


app = Flask(__name__)

node_id = str(uuid4()).replace('-', '')
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # we run proof of work algo to get the next proof
    last_proof = blockchain.last_block.proof
    proof = blockchain.proof_of_work(last_proof)

    # rewards for finding proof, sender is 0 to signify this node has mined a coin
    blockchain.new_transaction(sender="0", receiver=node_id, amount=1)

    # forge new block by adding it to the chan
    prev_hash = blockchain.hash(blockchain.last_block)
    new_block = blockchain.new_block(proof, prev_hash)

    response = {
        'message': "New Block Forged",
        'index': new_block.index,
        'transactions': [t.get_details() for t in new_block.transaction],
        'proof': new_block.proof,
        'previous_hash': new_block.previous_hash,
    }
    return json.dumps(response, cls=ComplexEncoder), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'receiver', 'amount']

    # check request has all required values
    if not all(k in values for k in required):
        return 'Missing values', 400

    index = blockchain.new_transaction(values['sender'], values['receiver'], values['amount'])
    response = {'message': f'Transaction will be added to the Block {index}'}

    return json.dumps(response, cls=ComplexEncoder), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': [block.get_details() for block in blockchain.chain],
        'length': len(blockchain.chain)
    }
    return json.dumps(response, cls=ComplexEncoder), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return json.dumps(response, cls=ComplexEncoder), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': [block.get_details() for block in blockchain.chain]
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': [block.get_details() for block in blockchain.chain]
        }
    return json.dumps(response, cls=ComplexEncoder), 200


if __name__== '__main__':
    # runs on localhost port 5000
    app.run(host='0.0.0.0', port=5000)