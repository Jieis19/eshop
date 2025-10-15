from flask import Flask, render_template, request, redirect, session
import hashlib, datetime

app = Flask(__name__)
app.secret_key = "123564"  # 必須設定，用於 session 加密

# 綠界測試金鑰
MERCHANT_ID = '2000132'
HASH_KEY = '5294y06JbISpM5x9'
HASH_IV = 'v77hoKGq4kWxNNIS'

# 商品清單
PRODUCTS = [
    {'id': 1, 'name': '產品A', 'price': 1000},
    {'id': 2, 'name': '產品B', 'price': 2000},
    {'id': 3, 'name': '產品C', 'price': 3000},
]

# 首頁
@app.route('/')
def index():
    return render_template('index.html', products=PRODUCTS)
@app.route('/book', methods=['GET'])
def book():
    return render_template('book.html')
# 加入購物車
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = int(request.form.get('product_id', 0))
    quantity = int(request.form.get('quantity', 1))

    if product_id == 0 or quantity <= 0:
        return "錯誤的商品或數量", 400

    # 建立 session 購物車
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    # 若商品已存在，累加數量
    if str(product_id) in cart:
        cart[str(product_id)] += quantity
    else:
        cart[str(product_id)] = quantity

    session['cart'] = cart
    return redirect('/cart')

# 顯示購物車
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

# 結帳導向綠界
@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return "購物車為空", 400

    total = sum(next(p['price'] for p in PRODUCTS if p['id'] == int(pid)) * qty for pid, qty in cart.items())
    item_name = " | ".join([f"{next(p['name'] for p in PRODUCTS if p['id']==int(pid))} x {qty}" for pid, qty in cart.items()])

    params = {
        "MerchantID": MERCHANT_ID,
        "MerchantTradeNo": f"EC{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "MerchantTradeDate": datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
        "PaymentType": "aio",
        "TotalAmount": total,
        "TradeDesc": "購物車結帳",
        "ItemName": item_name,
        "ReturnURL": "https://你的Render網址.com/receive",
        "ChoosePayment": "ALL",
    }

    check_value = f"HashKey={HASH_KEY}&" + "&".join([f"{k}={v}" for k,v in params.items()]) + f"&HashIV={HASH_IV}"
    params['CheckMacValue'] = hashlib.md5(check_value.encode('utf-8')).hexdigest().upper()

    html_form = "<form id='ecpay_form' method='post' action='https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5'>"
    for k,v in params.items():
        html_form += f"<input type='hidden' name='{k}' value='{v}'>"
    html_form += "</form><script>document.getElementById('ecpay_form').submit();</script>"

    # 清空購物車
    session['cart'] = {}
    return html_form

# 綠界回傳結果
@app.route('/receive', methods=['POST'])
def receive():
    data = request.form
    return render_template('result.html', data=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
