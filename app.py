import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # user's stock and shares
    stocks = db.execute("SELECT symbol, SUM(shares) as total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0", session["user_id"])

    # user's cash
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]

    total_value = cash
    #total = cash

    for stock in stocks:
        quote = lookup (stock["symbol"])
        stock["name"] = quote["name"]
        stock["price"] = quote["price"]
        stock["value"] = stock["price"] * stock["total_shares"]
        total_value += stock["value"]
        #total += stock["value"]

    return render_template("index.html", stocks=stocks, cash=cash, total_value=total_value)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # user reach route via POST
    if request.method == "POST":

        # get input of user as variables
        buy_symbol = request.form.get("symbol")
        buy_shares = request.form.get("shares")

        if not buy_symbol:
            return apology("missing symbol")

        elif not buy_shares:
            return apology("missing shares")
        elif not buy_shares.isdigit():
            return apology("invalid shares")
        elif int(buy_shares) <= 0:
            return apology("invalid shares")

        # use lookup function to make dictionary of buying
        buy_dict = lookup(buy_symbol)

        if buy_dict == None:
            return apology("symbol doesn't exist")

        # value of transaction
        shares = int(buy_shares)
        buy_transaction = shares * buy_dict["price"]

        # check if user has enough cash for buying
        user_cash = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])
        cash = user_cash[0]["cash"]

        # substract user_cash by value of buying
        update_cash = cash - buy_transaction

        if update_cash < 0:
            return apology("Cash is not enough")
        else:
            # Update user account (cash) after the transaction
            db.execute("UPDATE users SET cash = ? WHERE id = ?", update_cash, session["user_id"]);

            # Update the transactions table
            db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)", session["user_id"], buy_dict["symbol"], shares, buy_dict["price"])
            flash("Bought!")

        return redirect("/")

    else:
        # user reach route via GET (link or via redirect)
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # look through transaction
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC" , session["user_id"])

    # present history page with transactions
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        stocksymbol = request.form.get("symbol").upper()

        # make a dictionary with 3 keys: name, price, symbol based on lookup function in helpers.py
        stock_quote = lookup(stocksymbol)
        if not stock_quote:
            return apology("missing stock symbol")
        else:
            company_name = stock_quote["name"]
            price = stock_quote["price"]
            symbol = stock_quote["symbol"]
            return render_template("quoted.html", name=company_name, symbol=symbol, price=price)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # get user information via POST
    if request.method == "POST":
        username = request.form.get("username")
        # check if username blank
        if not username:
            return apology("missing username")
        #check if username already exist
        user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(user) != 0:
            return apology("username already exist")

        password = request.form.get("password")
        #check if password blank
        if not password:
            return apology("missing password")

        confirmation = request.form.get("confirmation")
        #check if not confirm and not match
        if not confirmation:
            return apology("missing confirmation")
        elif password != confirmation:
            return apology("password doesn't match")

        hash_password = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES(?,?)", username, hash_password)

        return redirect("/")
    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # get user stocks
    #stocks = db.execute("SELECT symbol, SUM(shares) AS total_shares FROM transactions WHERE id = ? GROUP BY symbol HAVING total_shares > 0", session["user_id"])

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # check if symbol and shares are not empty and valid
        if not symbol:
            return apology("missing symbol")
        elif not shares or not shares.isdigit():
            return apology("invalid number")
        elif int(shares) <= 0:
            return apology("invalid number")

        quote = lookup(symbol)
        if quote is None:
            return apology("symbol not found")

        shares = int(shares)
        price = quote["price"]
        sale = shares * price

        # get user stocks
        stocks = db.execute("SELECT symbol, SUM(shares) AS total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0", session["user_id"])
        if not stocks:
            return apology("no stocks found")

        for stock in stocks:
            if stock["total_shares"] < shares:
                return apology("too much shares")
            else:
                # update user's shares
                #updated_shares = stock["total_shares"] - shares
                #db.execute("UPDATE transactions SET shares = ? WHERE id = ?", updated_shares, session["user_id"])

                # update cash
                cash = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])[0]["cash"]
                updated_cash = cash + sale
                db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, session["user_id"] )

                # insert sale into history table
                db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?,?,?,?)", session["user_id"], symbol, -shares, price)

                flash("SOLD!")

                return redirect("/")

    else:
        stocks = db.execute("SELECT DISTINCT symbol, * FROM transactions WHERE user_id = ?", session["user_id"])
        return render_template("sell.html", stocks = stocks)
