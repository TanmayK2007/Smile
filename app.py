from flask import Flask, render_template, redirect, request, session
import sqlite3
from sqlite3 import Error
from flask_bcrypt import Bcrypt

DATABASE = "C:/Users/22452/OneDrive - Wellington College/13DTS/Smile/Cafe_DB"

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = "ueuywq9571"


def create_connection(db_file):
    """
    Create a connection with the database
    parameter: name of the database file
    returns: a connection to the file
    """
    try:
        connection = sqlite3.connect(db_file)
        return connection
    except Error as e:
        print(e)
    return None


def is_logged_in():
    if session.get("email") is None:
        print("not logged in")
        return False
    else:
        print("logged in")
        return True


@app.route('/')
def render_home():
    message = request.args.get('message')
    if message is None:
        message = ""

    return render_template('home.html', logged_in=is_logged_in(), message=message, ordering=is_ordering())


def is_ordering():
    if session.get("order") is None:
        print("not ordering")
        return False
    else:
        print("ordering")
        return True


def get_list(query, params):
    con = create_connection(DATABASE)
    cur = con.cursor()
    if params == "":
        cur.execute(query)
    else:
        cur.execute(query, params)
    query_list = cur.fetchall()
    con.close()
    return query_list


def put_data(query, params):
    con = create_connection(DATABASE)
    cur = con.cursor()
    cur.execute(query, params)
    con.commit()
    con.close()


def summarise_order():
    order = session['order']
    print(order)
    order.sort()
    print(order)
    order_summary = []
    last_order = -1
    for item in order:
        if item != last_order:
            order_summary.append([item, 1])
            last_order = item
        else:
            order_summary[-1][1] += 1
    print(order_summary)
    return order_summary


@app.route('/menu/<cat_id>')
def render_menu(cat_id):
    category_list = get_list("SELECT * FROM category", "")
    product_list = get_list("SELECT * FROM Products"
                            " WHERE cat_id = ? ORDER BY name", (cat_id, ))
    order_start = request.args.get('order')
    if order_start == "start" and not is_ordering():
        session["order"] = []

    return render_template("menu.html", categories=category_list, products=product_list,
                           logged_in=is_logged_in(), ordering=is_ordering())


@app.route('/add_to_cart/<product_id>')
def add_to_cart(product_id):
    try:
        product_id = int(product_id)
    except ValueError:
        print("{} is not an integer".format(product_id))
        return redirect("/menu/1?error=Invalid+product+id")
    print("Adding to cart product", product_id)
    order = session['order']
    print("Order before adding", order)
    order.append(product_id)
    print("Order after adding", order)
    session['order'] = order
    return redirect(request.referrer)


@app.route('/cart', methods=['POST', 'GET'])
def render_cart():
    if request.method == "POST":
        name = request.form['name']
        print(name)
        put_data("INSERT INTO orders VALUES (null, ?, TIME('now'), ?)", (name, 1))
        order_number = get_list("SELECT max(id) FROM orders WHERE name = ?", (name, ))
        print(order_number)
        order_number = order_number[0][0]
        orders = summarise_order()
        for order in orders:
            put_data("INSERT INTO order_contents VALUES (null, ?, ?, ?)", (order_number, order[0], order[1]))
        session.pop('order')
        return redirect('/?message=Order+has+been+placed+under+the+name' + name)
    else:
        orders = summarise_order()
        total = 0
        for item in orders:
            item_detail = get_list("SELECT name, price FROM Products WHERE id = ?", (item[0], ))
            print(item_detail)
            if item_detail:
                item.append(item_detail[0][0])
                item.append(item_detail[0][1])
                item.append(item_detail[0][1] * item[1])
                total += item_detail[0][1] * item[1]
        print(orders)
        return render_template("cart.html", logged_in=is_logged_in(),
                               ordering=is_ordering(), products=orders, total=total)


@app.route('/process_orders/<processed>')
def render_processed_orders(processed):
    label = "processed"
    if processed == "1":
        label = "un" + label
    processed = int(processed)
    all_orders = get_list("SELECT orders.id, orders.name, timestamp, product.name, quantity, price FROM orders "
                          "INNER JOIN order_contents ON orders.id = order_contents.order_id "
                          "INNER JOIN products ON order_contents.product_id = product_id "
                          "WHERE processed = ?", (processed, ))


@app.route('/contact')
def render_contact():
    return render_template('contact.html', logged_in=is_logged_in())


@app.route('/login', methods=['POST', 'GET'])
def render_login():
    if is_logged_in():
        return redirect('/')
    print("Logging in")
    if request.method == "POST":
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()
        print(email)
        query = """SELECT id, fname, password FROM user WHERE email = ?"""
        con = create_connection(DATABASE)
        cur = con.cursor()
        cur.execute(query, (email,))
        user_data = cur.fetchall()
        con.close()
        print(user_data)
        # if given email is not in the database this will raise an error
        # would be better to find out how to see if the query return an empty result set
        if user_data is None:
            return redirect("/login?error=Email+invalid+password+incorrect")

        user_id = user_data[0][0]
        first_name = user_data[0][1]
        db_password = user_data[0][2]

        # check if the password is incorrect for that email address

        if not bcrypt.check_password_hash(db_password, password):
            return redirect(request.referrer + "?error=Email+invalid+or+password+incorrect")

        session['email'] = email
        session['user_id'] = user_id
        session['firstname'] = first_name

        print(session)
        return redirect('/')
    return render_template('login.html', logged_in=is_logged_in())


@app.route('/logout')
def logout():
    print(list(session.keys()))
    [session.pop(key) for key in list(session.keys())]
    print(list(session.keys()))
    return redirect('/?message=See+you+next+time!')


@app.route('/signup', methods=['POST', 'GET'])
def render_signup():
    if is_logged_in():
        return redirect('/menu/1')
    if request.method == 'POST':
        print(request.form)
        fname = request.form.get('fname').title()
        lname = request.form.get('lname').title().strip()
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')
        password2 = request.form.get('password2')

        if password != password2:
            return redirect("\signup?error=Passwords+do+not+match")

        if len(password) < 8:
            return redirect("\signup?error=Password+must+be+at+least+8+characters")

        hashed_password = bcrypt.generate_password_hash(password)
        con = create_connection(DATABASE)
        query = "INSERT INTO user (fname, lname, email, password) VALUES (?, ?, ?, ?)"
        cur = con.cursor()

        try:
            cur.execute(query, (fname, lname, email, hashed_password))
        except sqlite3.IntegrityError:
            con.close()
            return redirect('\signup?error=Email+is+already+used')

        con.commit()
        con.close()

        return redirect("\login")

    return render_template('signup.html', logged_in=is_logged_in())


@app.route('/admin')
def render_admin():
    if not is_logged_in():
        return redirect('/?message=Need+to+be+logged+in.')
    con = create_connection(DATABASE)
    query = "SELECT * FROM category"
    cur = con.cursor()
    cur.execute(query)
    category_list = cur.fetchall()
    con.close()
    return render_template("admin.html", logged_in=is_logged_in(), categories=category_list)


@app.route('/add_category', methods=['POST'])
def add_category():
    if not is_logged_in():
        return redirect('/?message=Need+to+be+logged+in.')
    if request.method == "POST":
        print(request.form)
        cat_name = request.form.get('name').lower().strip()
        print(cat_name)
        con = create_connection(DATABASE)
        query = "INSERT INTO category ('name') VALUES (?)"
        cur = con.cursor()
        cur.execute(query, (cat_name, ))
        con.commit()
        con.close()
        return redirect('/admin')


@app.route('/delete_category', methods=['POST'])
def render_delete_category():
    if not is_logged_in():
        return redirect('/?message=Need+to+be+logged+in.')
    if request.method == "POST":
        category = request.form.get('cat_id')
        print(category)
        category = category.split(", ")
        cat_id = category[0]
        cat_name = category[1]
        return render_template("delete_confirm.html", id=cat_id, name=cat_name, type="category")
    return redirect("/admin")


@app.route('/delete_category_confirm/<cat_id>')
def delete_category_confirm(cat_id):
    if not is_logged_in():
        return redirect('/?message=Need+to+be+logged+in.')
    con = create_connection(DATABASE)
    query = "DELETE FROM category WHERE id = ?"
    cur = con.cursor()
    cur.execute(query, (cat_id, ))
    con.commit()
    con.close()
    return redirect("/admin")


app.run(host='0.0.0.0', debug=True)
