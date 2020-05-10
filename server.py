from flask import Flask, request, render_template, redirect
from uuid import uuid4
from blockchain import Blockchain, ComplexEncoder
import json
import requests


app = Flask(__name__)

node_id = str(uuid4()).replace('-', '')
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # we run proof of work algo to get the next proof
    last_proof = blockchain.last_block.proof
    proof = blockchain.proof_of_work(last_proof)

    # rewards for finding proof, sender is 0 to signify this node has mined a coin
    blockchain.new_transaction(sender="minedCoin", receiver=node_id, amount=1)

    # forge new block by adding it to the chain
    prev_hash = blockchain.hash(blockchain.last_block)
    new_block = blockchain.new_block(proof, prev_hash)

    # check for consensus with peer nodes and announce new block if current blockchain is longest
    curr_len = len(blockchain.chain)
    consensus()
    if curr_len == len(blockchain.chain):
        # ours was longest so announce new mined node to the peers
        announce_new_block(blockchain.last_block)

    response = {
        'message': "New Block Forged",
        'index': new_block.index,
        'transactions': [t.get_details() for t in new_block.transaction],
        'proof': new_block.proof,
        'previous_hash': new_block.previous_hash,
    }
    return json.dumps(response, cls=ComplexEncoder), 200


def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for neighbour in blockchain.nodes:
        url = '{}/blocks/add'.format(neighbour)
        requests.post(url, data=json.dumps(block, cls=ComplexEncoder))


# endpoint to add a block mined by someone else to
# the node's chain. The node first verifies the block
# and then adds it to the chain.
@app.route('/blocks/add', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    last_proof = blockchain.last_block.proof
    curr_hash = blockchain.hash(blockchain.last_block)

    if curr_hash != block_data['previous_hash'] or last_proof != block_data['proof']:
        return "The block was discarded by the node, resolve conflicts with peers before adding", 400
    else:
        blockchain.new_block(index=block_data['index'], timestamp=block_data['timestamp'],
                             transaction=block_data['transactions'], proof=block_data['proof'],
                             previous_hash=block_data['previous_hash'])
    return "Block added to the chain", 201


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


@app.route('/transactions/pending', methods=['GET'])
def get_pending_tx():
    resp = {
        'Pending transactions': [t.get_details() for t in blockchain.currentTransactions]
    }
    return json.dumps(resp, cls=ComplexEncoder), 201


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
        return "Error: Please supply a valid (list) of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    # Return the blockchain to the newly registered node so that it can sync
    current_nodes_chain, status_code = full_chain()

    response = {
        'message': 'New nodes have been added',
        'peer_nodes': list(blockchain.nodes),
        'blockchain': current_nodes_chain
    }
    return json.dumps(response, cls=ComplexEncoder), 201


@app.route('/nodes/register_with', methods=['POST'])
def register_with_existing_node():
    """
    registers current node with the remote node specified in the request
    and sync the blkchain with the remote node's blkchain
    :return:
    """
    values = request.get_json()
    node = values.get('node')
    if not node:
        return 'Invalid request data', 400

    headers = {'Content-Type': "application/json"}
    data = {'nodes': [request.host_url]}
    response = requests.post(node + '/nodes/register', data=json.dumps(data), headers=headers)

    if response.status_code == 201:
        # build this nodes blockchain from the the remote's chain
        remote_chain_dump = response.json()['blockchain']['chain']
        new_chain = create_chain_from_dump(remote_chain_dump)

        # register remote's peer nodes to this nodes new_chain peers
        remote_chain_peers = response.json()['peer_nodes']
        for peer in remote_chain_peers:
            new_chain.register_node(peer)
        # add the remote node if not present
        if node not in blockchain.nodes:
            new_chain.register_node(node)
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    blockchain = Blockchain()
    for idx, block_data in enumerate(chain_dump):
        proof = block_data['proof']
        prev_hash = block_data['previous_hash']
        if idx > 0:
            added_block = blockchain.new_block(proof, prev_hash)
            if not added_block:
                raise Exception('The chain dump was tampered')
    return blockchain


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


if __name__ == '__main__':
    # runs on localhost port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
