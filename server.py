from flask import Flask, request, render_template, redirect
import random
from blockchain import Blockchain, ComplexEncoder
import json
import requests
from keygenerator import keygenerator


app = Flask(__name__)

# Generate random seed to feed the key gen
private_value = random.randint(1,10000)

# Init Key Generator to generate signing keys
KG = keygenerator(private_value)
KG.generate_keys()

# Set own wallet address to the public key hex string
node_wallet_id = KG.get_public_key()
if node_wallet_id is None or len(node_wallet_id) == 0:
    raise Exception('Node server unable to generate valid wallet ID')

# Init the blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # check for consensus with peer nodes before mining
    # ensures we have the largest blockchain copy
    if len(blockchain.nodes) != 0:
        consensus_response, status_code = consensus()
        if status_code != 200:
            return consensus_response, 400

    # we run proof of work algo to get the next proof
    last_proof = blockchain.last_block.proof
    proof = blockchain.proof_of_work(last_proof)

    # rewards for finding proof, sender is System to signify this node has mined a coin
    blockchain.new_transaction(sender="System", receiver=node_wallet_id, amount=blockchain.mining_reward)

    # forge new block by adding it to the chain
    prev_hash = blockchain.hash(blockchain.last_block)
    new_block = blockchain.new_block(proof=proof, previous_hash=prev_hash)

    # ours is longest chain now so announce new mined node to the peers
    announce_resp, status_code = announce_new_block()
    if status_code != 201:
        return announce_resp, 400

    response = {
        'message': "New Block Forged",
        'index': new_block.index,
        'transactions': [t.get_details() for t in new_block.transaction],
        'proof': new_block.proof,
        'previous_hash': new_block.previous_hash,
    }
    return json.dumps(response, cls=ComplexEncoder), 200


def announce_new_block():
    """
    A function to announce to the network once a block has been mined.
    Other nodes can verify the longest chain and reach consensus
    """

    headers = {'Content-Type': "application/json"}
    for neighbour in blockchain.nodes:
        url = f'http://{neighbour}/nodes/resolve'
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f'Message from peer node: {neighbour}, {response.text}, {response.reason}')

    return "Finished announcing new block to peer chains", 201


@app.route('/blocks/add', methods=['POST'])
def verify_and_add_block(block_obj=None):
    """
    Add a block from request or block object.
    The node first verifies the block
    and then adds it to the chain.
    :param block_obj: Type Block
    :return:
    """
    if block_obj:
        block_data = block_obj.get_details()
    else:
        block_data = request.get_json()

    last_proof = blockchain.last_block.proof
    last_hash = blockchain.hash(blockchain.last_block)

    # check if the block to be added is valid for this blockchain
    if last_hash != block_data['previous_hash'] or not blockchain.is_valid_proof(last_proof, block_data['proof']):
        return "The block was discarded by the peer node, resolve conflicts with peers before adding", 400
    else:
        for tr in block_data['transactions']:
            blockchain.new_transaction(tr['sender'], tr['receiver'], tr['amount'], private_value)
        blockchain.new_block(index=block_data['index'], timestamp=block_data['timestamp'],
                             proof=block_data['proof'], previous_hash=block_data['previous_hash'])

    return "Block added to the peer's chain", 201


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['receiver', 'amount']

    # check request has all required values
    if not all(k in values for k in required):
        return 'Missing values', 400

    index = blockchain.new_transaction(node_wallet_id, values['receiver'], values['amount'], private_value)
    response = {'message': f'Transaction will be added to the Block {index}'}

    return json.dumps(response, cls=ComplexEncoder), 201


@app.route('/transactions/pending', methods=['GET'])
def get_pending_transactions():
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
        'blockchain': json.loads(current_nodes_chain)
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
    remote_node = values.get('node')
    if not remote_node:
        return 'Invalid request data', 400

    headers = {'Content-Type': "application/json"}
    data = {'nodes': [request.host_url]}
    response = requests.post(remote_node + '/nodes/register', data=json.dumps(data), headers=headers)

    if response.status_code == 201:
        # build this nodes blockchain from the the remote's chain
        remote_chain_dump = response.json()['blockchain']['chain']
        blockchain.register_with_chain(remote_chain_dump)

        # register remote's peer nodes to this nodes new_chain peers
        remote_chain_peers = response.json()['peer_nodes']
        for peer in remote_chain_peers:
            blockchain.register_node(peer)
        # add the remote node if not present
        if remote_node not in blockchain.nodes:
            blockchain.register_node(remote_node)
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code

    # get new chain contents
    new_chain, status_code = full_chain()

    response = {
        'message': 'Blockchain has been registered with remote node',
        'blockchain': json.loads(new_chain)
    }
    return json.dumps(response, cls=ComplexEncoder), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    try:
        replaced = blockchain.resolve_conflicts(private_value)
    except Exception as exp:
        return f'Error occurred while creating consensus: {exp}', 400

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': [block.get_details() for block in blockchain.chain],
            'replaced': 'True'
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': [block.get_details() for block in blockchain.chain],
            'replaced': 'False'
        }
    return json.dumps(response, cls=ComplexEncoder), 200


if __name__ == '__main__':
    print(private_value)
    # runs on localhost port 5000
    app.run(debug=True, host='127.0.0.1', port=5000)

    # export FLASK_APP=server.py
    # flask run --port 5001
    # flask run --port 5000

    # Sample request for creating new transaction
    """
    curl -X POST -H "Content-Type: application/json" -d '{
     "sender": "d4ee26eee15148ee92c6cd394edd974e",
     "receiver": "someone",
     "amount": 5
    }' "http://127.0.0.1:5000/transactions/new"
    """

    # Register peer Nodes
    """
    curl -X POST -H "Content-Type: application/json" -d '{"nodes": ["http://127.0.0.1:5001"]}' "http://127.0.0.1:5000/nodes/register"
    """
