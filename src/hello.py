from flask import Flask, jsonify

# Initialize Flask application
app = Flask(__name__)

# Define the API endpoint
@app.route('/api/hello', methods=['GET'])
def hello_spencer():
    f = open("count.txt","r")
    counter = int(f.read())
    f.close()
    counter += 1
    f = open("count.txt","w")
    f.write(str(counter))
    f.close()

    return jsonify({
        "message": "Hello Spencer",
        "counter" : counter,
        "status": "success"
    })

# Run the application
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5556)
