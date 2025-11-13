from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def home():
    """Render the RouteMind product overview."""
    return render_template("index.html")


@app.route("/command-center")
def command_center():
    """Render the dispatcher control centre dashboard."""
    return render_template("command_center.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
