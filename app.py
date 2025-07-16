from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect', methods=['POST'])
def connect():
    ip = request.form['ip']
    username = request.form['username']
    password = request.form['password']

    # ✅ MOCK OUTPUT: Simulated switch command result
    output = f"""
    Switch connection to {ip} was successful!
    
    Port    Name       Status       Vlan
    Gi0/1   AdminPC    connected    10
    Gi0/2   HR-PC      notconnect   20
    Gi0/3   Camera     connected    30
    Gi0/4              err-disabled 1
    """

    return f"<h2>Switch Output:</h2><pre>{output}</pre><a href='/'>Back</a>"

@app.route('/test')
def test():
    return "Test route is working!"

if __name__ == '__main__':
    app.run(debug=True)
