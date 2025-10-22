from flask import Flask, render_template, request, redirect, session
import hashlib, datetime, json, base64
from Crypto.Cipher import AES  # pip install pycryptodome
import urllib.parse

app = Flask(__name__)
app.secret_key = "123564"

# 🔹 藍新測試金鑰
MERCHANT_ID = 'MS1804320480'
HASH_KEY = 'KYLDPubJWMXhqokhFoAzowviMFba4A0N'
HASH_IV = 'PMi9PKSrwXsJbx8C'

# 🔹 付款網址
NEWEBPAY_URL = "https://core.newebpay.com/MPG/mpg_gateway"

# 商品清單
PRODUCTS = [
    {'id': 1, 'name': '產品A', 'price': 1000},
    {'id': 2, 'name': '產品B', 'price': 2000},
    {'id': 3, 'name': '產品C', 'price': 3000},
]

# ---------- 工具函式 ----------
def pad(data):
    """PKCS7 padding"""
    block_size = 32
    padding_len = block_size - (len(data) % block_size)
    return data + (chr(padding_len) * padding_len)

def aes_encrypt(data):
    """AES256-CBC 加密"""
    cipher = AES.new(HASH_KEY.encode('utf-8'), AES.MODE_CBC, HASH_IV.encode('utf-8'))
    padded_data = pad(data)
    encrypted_bytes = cipher.encrypt(padded_data.encode('utf-8'))
    return encrypted_bytes.hex()

def sha256_encode(trade_info):
    """產生 TradeSha"""
    raw = f"HashKey={HASH_KEY}&{trade_info}&HashIV={HASH_IV}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()

# ---------- 路由 ----------
@app.route('/')
def index():
    return render_template('index.html', products=PRODUCTS)

@app.route('/book', methods=['GET'])
def book():
    return render_template('book.html')

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = int(request.form.get('product_id', 0))
    quantity = int(request.form.get('quantity', 1))

    if product_id == 0 or quantity <= 0:
        return "錯誤的商品或數量", 400

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    if str(product_id) in cart:
        cart[str(product_id)] += quantity
    else:
        cart[str(product_id)] = quantity

    session['cart'] = cart
    return redirect('/cart')

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    items = []
    total = 0

    for pid, qty in cart.items():
        product = next((p for p in PRODUCTS if p['id'] == int(pid)), None)
        if product:
            subtotal = product['price'] * qty
            items.append({'product': product, 'quantity': qty, 'subtotal': subtotal})
            total += subtotal

    return render_template('cart.html', items=items, total=total)

@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return "購物車為空", 400

    total = sum(next(p['price'] for p in PRODUCTS if p['id'] == int(pid)) * qty for pid, qty in cart.items())
    item_name = " | ".join([f"{next(p['name'] for p in PRODUCTS if p['id']==int(pid))} x {qty}" for pid, qty in cart.items()])

    trade_no = f"NW{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    trade_data = {
        "MerchantID": MERCHANT_ID,
        "RespondType": "JSON",
        "TimeStamp": str(int(datetime.datetime.now().timestamp())),
        "Version": "2.0",
        "MerchantOrderNo": trade_no,
        "Amt": total,
        "ItemDesc": item_name,
        "Email": "test@example.com",
        "ReturnURL": "https://eshop-5a2r.onrender.com/receive",
        "NotifyURL": "https://eshop-5a2r.onrender.com/receive",
        "LoginType": 0,
    }

    trade_query = urllib.parse.urlencode(trade_data)
    trade_info = aes_encrypt(trade_query)
    trade_sha = sha256_encode(trade_info)

    html_form = f"""
    <form id='newebpay_form' method='post' action='{NEWEBPAY_URL}'>
        <input type='hidden' name='MerchantID' value='{MERCHANT_ID}'>
        <input type='hidden' name='TradeInfo' value='{trade_info}'>
        <input type='hidden' name='TradeSha' value='{trade_sha}'>
        <input type='hidden' name='Version' value='2.0'>
    </form>
    <script>document.getElementById('newebpay_form').submit();</script>
    """

    session['cart'] = {}
    return html_form

@app.route('/receive', methods=['POST'])
def receive():
    data = request.form.to_dict()
    return render_template('result.html', data=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
