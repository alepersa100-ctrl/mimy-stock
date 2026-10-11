import os
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mimy_stock_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mimystock.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

COLOMBIA_TZ = pytz.timezone('America/Bogota')

def get_colombia_time():
    return datetime.now(COLOMBIA_TZ)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'employee', 'producer'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    product_type = db.Column(db.String(30), nullable=False)
    stock = db.Column(db.Float, nullable=False)
    price_per_unit = db.Column(db.Float, default=0.0)
    tray_size = db.Column(db.Integer, default=7)
    tray_price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Combo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    items = db.relationship('ComboItem', backref='combo', cascade='all, delete-orphan')

class ComboItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    combo_id = db.Column(db.Integer, db.ForeignKey('combo.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    trays_required = db.Column(db.Float, nullable=False)
    product_ref = db.relationship('Product')

class Supply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    stock = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    min_stock = db.Column(db.Float, default=2.0)
    is_active = db.Column(db.Boolean, default=True)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    is_corporate = db.Column(db.Boolean, default=False)

class CreditAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    client = db.relationship('Client', backref='credit_account')
    total_debt = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.String(50), nullable=False)
    transactions = db.relationship('CreditTransaction', backref='account', cascade='all, delete-orphan')

class CreditTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('credit_account.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(250), nullable=False)
    amount_charged = db.Column(db.Float, default=0.0)
    amount_paid = db.Column(db.Float, default=0.0)
    seller = db.Column(db.String(100), nullable=False)

class AccountPayable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider_name = db.Column(db.String(150), nullable=False)
    concept = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Pendiente')
    registered_date = db.Column(db.String(50), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(150), nullable=False)
    scheduled_date = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Pendiente')
    payment_type = db.Column(db.String(30), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    advance_payment = db.Column(db.Float, default=0.0)
    remaining_balance = db.Column(db.Float, nullable=False)
    seller = db.Column(db.String(100), nullable=False)
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    sale_mode = db.Column(db.String(20), nullable=True)
    quantity = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

class CashRegister(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50), nullable=False)
    initial_cash = db.Column(db.Float, nullable=False)
    total_sales = db.Column(db.Float, default=0.0)
    final_cash = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Abierta')

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_sold = db.Column(db.String(50), nullable=False)
    seller = db.Column(db.String(100), nullable=False)
    client_name = db.Column(db.String(150), nullable=True)
    total_amount = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(30), default='Efectivo')
    items = db.relationship('SaleItem', backref='sale', cascade='all, delete-orphan')

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    quantity_sold = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password=generate_password_hash('1234', method='pbkdf2:sha256'), role='admin'))
    if not User.query.filter_by(username='empleado').first():
        db.session.add(User(username='empleado', password=generate_password_hash('1234', method='pbkdf2:sha256'), role='employee'))
    if not User.query.filter_by(username='produccion').first():
        db.session.add(User(username='produccion', password=generate_password_hash('1234', method='pbkdf2:sha256'), role='producer'))
    db.session.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    today = get_colombia_time().strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        if request.form.get('add_product') == '1' and current_user.role == 'admin':
            name = request.form.get('name')
            product_type = request.form.get('product_type')
            stock = float(request.form.get('stock'))
            tray_price = float(request.form.get('tray_price'))
            tray_size = int(request.form.get('tray_size', 7))
            price_per_unit = float(request.form.get('price_per_unit', 0)) if product_type == 'grande' else 0.0

            db.session.add(Product(
                name=name,
                product_type=product_type,
                stock=stock,
                price_per_unit=price_per_unit,
                tray_size=tray_size,
                tray_price=tray_price,
                is_active=True
            ))
            db.session.commit()

        elif request.form.get('edit_product') == '1' and current_user.role == 'admin':
            p_id = int(request.form.get('product_id'))
            prod = Product.query.get(p_id)
            if prod:
                prod.name = request.form.get('name')
                prod.stock = float(request.form.get('stock'))
                prod.tray_price = float(request.form.get('tray_price'))
                prod.tray_size = int(request.form.get('tray_size', 7))
                if prod.product_type == 'grande':
                    prod.price_per_unit = float(request.form.get('price_per_unit', 0))
                db.session.commit()

        elif request.form.get('add_combo') == '1' and current_user.role == 'admin':
            combo_name = request.form.get('combo_name')
            combo_price = float(request.form.get('combo_price'))
            
            new_combo = Combo(name=combo_name, price=combo_price, is_active=True)
            db.session.add(new_combo)
            db.session.commit()

            prod_ids = request.form.getlist('combo_prod_id')
            req_trays = request.form.getlist('combo_req_trays')

            for p_id_str, t_str in zip(prod_ids, req_trays):
                if p_id_str and t_str:
                    db.session.add(ComboItem(
                        combo_id=new_combo.id,
                        product_id=int(p_id_str),
                        trays_required=float(t_str)
                    ))
            db.session.commit()

        elif request.form.get('add_supply') == '1' and current_user.role == 'admin':
            db.session.add(Supply(
                name=request.form.get('supply_name'),
                stock=float(request.form.get('supply_stock')),
                unit=request.form.get('supply_unit'),
                min_stock=float(request.form.get('supply_min', 2.0)),
                is_active=True
            ))
            db.session.commit()

        elif request.form.get('add_payable') == '1' and current_user.role == 'admin':
            db.session.add(AccountPayable(
                provider_name=request.form.get('provider_name'),
                concept=request.form.get('concept'),
                amount=float(request.form.get('amount')),
                due_date=request.form.get('due_date'),
                status='Pendiente',
                registered_date=get_colombia_time().strftime('%Y-%m-%d %H:%M:%S')
            ))
            db.session.commit()

        elif request.form.get('add_client') == '1' and current_user.role in ['admin', 'employee']:
            is_corp = True if request.form.get('is_corporate') == 'on' else False
            new_client = Client(
                name=request.form.get('client_name'),
                phone=request.form.get('client_phone'),
                address=request.form.get('client_address'),
                is_corporate=is_corp
            )
            db.session.add(new_client)
            db.session.commit()

            if is_corp:
                if not CreditAccount.query.filter_by(client_id=new_client.id).first():
                    db.session.add(CreditAccount(
                        client_id=new_client.id,
                        total_debt=0.0,
                        last_updated=get_colombia_time().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    db.session.commit()

        elif request.form.get('add_order') == '1' and current_user.role in ['admin', 'employee']:
            client_name = request.form.get('order_client')
            scheduled_date = request.form.get('scheduled_date')
            payment_type = request.form.get('payment_type')
            advance_payment = float(request.form.get('advance_payment', 0.0) or 0.0)

            item_types = request.form.getlist('order_item_type')
            item_ids = request.form.getlist('order_item_id')
            sale_modes = request.form.getlist('order_sale_mode')
            quantities = request.form.getlist('order_qty')

            order_items_data = []
            total_order_amount = 0.0

            for itype, i_id_str, smode, qty_str in zip(item_types, item_ids, sale_modes, quantities):
                if itype and i_id_str and qty_str:
                    qty = float(qty_str)
                    if qty > 0:
                        if itype == 'product':
                            prod = Product.query.get(int(i_id_str))
                            if prod:
                                if prod.product_type == 'grande':
                                    if smode == 'tray':
                                        subtotal = qty * prod.tray_price
                                        item_name = f"Bandeja grande de {prod.name} (x{prod.tray_size})"
                                    else:
                                        subtotal = qty * prod.price_per_unit
                                        item_name = f"{prod.name} (Unidad suelta)"
                                else:
                                    subtotal = qty * prod.tray_price
                                    item_name = f"Bandeja pequeña de {prod.name} (x{prod.tray_size})"

                                order_items_data.append({
                                    'item_type': 'product',
                                    'item_id': prod.id,
                                    'item_name': item_name,
                                    'sale_mode': smode,
                                    'quantity': qty,
                                    'subtotal': subtotal
                                })
                                total_order_amount += subtotal
                        elif itype == 'combo':
                            combo = Combo.query.get(int(i_id_str))
                            if combo:
                                subtotal = qty * combo.price
                                order_items_data.append({
                                    'item_type': 'combo',
                                    'item_id': combo.id,
                                    'item_name': f"Combo: {combo.name}",
                                    'sale_mode': '',
                                    'quantity': qty,
                                    'subtotal': subtotal
                                })
                                total_order_amount += subtotal

            if order_items_data:
                if payment_type == 'Anticipado':
                    advance_payment = total_order_amount
                elif payment_type == 'Contraentrega':
                    advance_payment = 0.0

                remaining_balance = total_order_amount - advance_payment

                new_order = Order(
                    client_name=client_name,
                    scheduled_date=scheduled_date,
                    status='Pendiente',
                    payment_type=payment_type,
                    total_amount=total_order_amount,
                    advance_payment=advance_payment,
                    remaining_balance=remaining_balance,
                    seller=current_user.username
                )
                db.session.add(new_order)
                db.session.commit()

                for oitem in order_items_data:
                    db.session.add(OrderItem(
                        order_id=new_order.id,
                        item_type=oitem['item_type'],
                        item_id=oitem['item_id'],
                        item_name=oitem['item_name'],
                        sale_mode=oitem['sale_mode'],
                        quantity=oitem['quantity'],
                        subtotal=oitem['subtotal']
                    ))
                db.session.commit()

        elif request.form.get('make_sale') == '1' and current_user.role in ['admin', 'employee']:
            client_name = request.form.get('client_name', 'Cliente General')
            payment_method = request.form.get('payment_method', 'Efectivo')
            item_types = request.form.getlist('item_type')
            item_ids = request.form.getlist('item_id')
            sale_modes = request.form.getlist('sale_mode')
            quantities = request.form.getlist('qty_to_sell')
            
            sale_details = []
            total_sale_amount = 0.0

            for itype, i_id_str, smode, qty_str in zip(item_types, item_ids, sale_modes, quantities):
                if itype and i_id_str and qty_str:
                    qty = float(qty_str)
                    if qty > 0:
                        if itype == 'product':
                            prod = Product.query.get(int(i_id_str))
                            if prod:
                                if prod.product_type == 'grande':
                                    if smode == 'tray':
                                        subtotal = qty * prod.tray_price
                                        units_to_deduct = qty * prod.tray_size
                                        item_desc = f"Bandeja grande de {prod.name} (x{prod.tray_size})"
                                    else:
                                        subtotal = qty * prod.price_per_unit
                                        units_to_deduct = qty
                                        item_desc = f"{prod.name} (Unidad suelta)"
                                else:
                                    subtotal = qty * prod.tray_price
                                    units_to_deduct = qty
                                    item_desc = f"Bandeja pequeña de {prod.name} (x{prod.tray_size} unids)"

                                sale_details.append({
                                    'type': 'product',
                                    'obj': prod,
                                    'units_to_deduct': units_to_deduct,
                                    'qty': qty,
                                    'desc': item_desc,
                                    'subtotal': subtotal
                                })
                                total_sale_amount += subtotal
                        elif itype == 'combo':
                            combo = Combo.query.get(int(i_id_str))
                            if combo:
                                sale_details.append({
                                    'type': 'combo',
                                    'obj': combo,
                                    'qty': qty,
                                    'subtotal': qty * combo.price
                                })
                                total_sale_amount += qty * combo.price

            if sale_details:
                fecha_actual = get_colombia_time().strftime('%Y-%m-%d %H:%M:%S')
                
                if payment_method == 'Credito':
                    client_obj = Client.query.filter_by(name=client_name).first()
                    if not client_obj or not client_obj.is_corporate:
                        payment_method = 'Efectivo'

                new_sale = Sale(
                    date_sold=fecha_actual,
                    seller=current_user.username,
                    client_name=client_name,
                    total_amount=total_sale_amount,
                    payment_method=payment_method
                )
                db.session.add(new_sale)
                db.session.commit()

                for item in sale_details:
                    if item['type'] == 'product':
                        prod = item['obj']
                        prod.stock -= item['units_to_deduct']
                        db.session.add(SaleItem(
                            sale_id=new_sale.id,
                            product_name=item['desc'],
                            quantity_sold=item['qty'],
                            subtotal=item['subtotal']
                        ))
                    elif item['type'] == 'combo':
                        combo = item['obj']
                        combo_qty = item['qty']
                        for c_item in combo.items:
                            c_item.product_ref.stock -= c_item.trays_required * combo_qty
                        db.session.add(SaleItem(
                            sale_id=new_sale.id,
                            product_name=f"Combo: {combo.name}",
                            quantity_sold=combo_qty,
                            subtotal=item['subtotal']
                        ))
                
                db.session.commit()
                
                if payment_method == 'Credito':
                    client_obj = Client.query.filter_by(name=client_name).first()
                    if client_obj:
                        credit_acc = CreditAccount.query.filter_by(client_id=client_obj.id).first()
                        if not credit_acc:
                            credit_acc = CreditAccount(client_id=client_obj.id, total_debt=0.0, last_updated=fecha_actual)
                            db.session.add(credit_acc)
                            db.session.commit()
                        
                        credit_acc.total_debt += total_sale_amount
                        credit_acc.last_updated = fecha_actual
                        db.session.add(CreditTransaction(
                            account_id=credit_acc.id,
                            date=fecha_actual,
                            description=f"Venta a Crédito - Ticket #{new_sale.id}",
                            amount_charged=total_sale_amount,
                            amount_paid=0.0,
                            seller=current_user.username
                        ))
                        db.session.commit()

                if payment_method != 'Credito':
                    current_box = CashRegister.query.filter_by(date=today, status='Abierta').first()
                    if current_box:
                        sales_today = Sale.query.filter(Sale.date_sold.startswith(today), Sale.payment_method != 'Credito').all()
                        current_box.total_sales = sum(s.total_amount for s in sales_today)
                        current_box.final_cash = current_box.initial_cash + current_box.total_sales
                        db.session.commit()

                return redirect(url_for('receipt', sale_id=new_sale.id))
        
        elif request.form.get('manage_cash') == '1' and current_user.role == 'admin':
            action = request.form.get('cash_action')
            if action == 'open':
                initial = float(request.form.get('initial_cash'))
                existing_c = CashRegister.query.filter_by(date=today, status='Abierta').first()
                if not existing_c:
                    db.session.add(CashRegister(date=today, initial_cash=initial, status='Abierta'))
                    db.session.commit()
            elif action == 'close':
                box = CashRegister.query.filter_by(date=today, status='Abierta').first()
                if box:
                    sales_today = Sale.query.filter(Sale.date_sold.startswith(today), Sale.payment_method != 'Credito').all()
                    total_s = sum(s.total_amount for s in sales_today)
                    box.total_sales = total_s
                    box.final_cash = box.initial_cash + total_s
                    box.status = 'Cerrada'
                    db.session.commit()

        return redirect(url_for('index'))

    products = Product.query.filter_by(is_active=True).all()
    combos = Combo.query.filter_by(is_active=True).all()
    supplies = Supply.query.filter_by(is_active=True).all()
    clients = Client.query.all()
    orders = Order.query.filter(Order.status == 'Pendiente').all()
    credit_accounts = CreditAccount.query.all()
    payables = AccountPayable.query.all()
    
    filter_type = request.args.get('filter_type', 'month')
    selected_date = request.args.get('date', today)
    selected_month = request.args.get('month', get_colombia_time().strftime('%Y-%m'))
    
    if filter_type == 'day' and selected_date:
        sales = Sale.query.filter(Sale.date_sold.startswith(selected_date)).all()
        total_filtered_sales = sum(s.total_amount for s in sales if s.payment_method != 'Credito')
        filter_label = f"Día: {selected_date}"
    elif filter_type == 'month' and selected_month:
        sales = Sale.query.filter(Sale.date_sold.startswith(selected_month)).all()
        total_filtered_sales = sum(s.total_amount for s in sales if s.payment_method != 'Credito')
        filter_label = f"Mes: {selected_month}"
    else:
        sales = Sale.query.all()
        total_filtered_sales = sum(s.total_amount for s in sales if s.payment_method != 'Credito')
        filter_label = "Histórico Completo"

    current_cash = CashRegister.query.filter_by(date=today, status='Abierta').first()
    if not current_cash:
        current_cash = CashRegister.query.filter_by(date=today, status='Cerrada').first()
    
    return render_template(
        'index.html', 
        products=products, 
        combos=combos,
        supplies=supplies, 
        clients=clients, 
        orders=orders,
        credit_accounts=credit_accounts,
        payables=payables,
        sales=sales, 
        current_cash=current_cash,
        selected_date=selected_date,
        selected_month=selected_month,
        filter_type=filter_type,
        filter_label=filter_label,
        total_filtered_sales=total_filtered_sales
    )

@app.route('/credit/payment/<int:account_id>', methods=['POST'])
@login_required
def credit_payment(account_id):
    if current_user.role != 'admin':
        return "Acceso denegado", 403
    
    account = CreditAccount.query.get_or_404(account_id)
    payment_amount = float(request.form.get('payment_amount', 0))
    
    if payment_amount > 0:
        fecha_actual = get_colombia_time().strftime('%Y-%m-%d %H:%M:%S')
        account.total_debt -= payment_amount
        if account.total_debt < 0:
            account.total_debt = 0.0
        account.last_updated = fecha_actual
        
        db.session.add(CreditTransaction(
            account_id=account.id,
            date=fecha_actual,
            description="Pago / Abono de Cierre de Mes",
            amount_charged=0.0,
            amount_paid=payment_amount,
            seller=current_user.username
        ))
        db.session.commit()

        today = get_colombia_time().strftime('%Y-%m-%d')
        current_box = CashRegister.query.filter_by(date=today, status='Abierta').first()
        if current_box:
            current_box.final_cash += payment_amount
            db.session.commit()

    return redirect(url_for('index'))

@app.route('/payable/pay/<int:payable_id>')
@login_required
def pay_payable(payable_id):
    if current_user.role != 'admin':
        return "Acceso denegado", 403
    payable = AccountPayable.query.get_or_404(payable_id)
    payable.status = 'Pagado'
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/restock/product/<int:product_id>', methods=['POST'])
@login_required
def restock_product(product_id):
    if current_user.role not in ['admin', 'producer']:
        return "Acceso denegado", 403
    prod = Product.query.get_or_404(product_id)
    add_qty = float(request.form.get('add_qty', 0))
    if add_qty > 0:
        prod.stock += add_qty
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/restock/supply/<int:supply_id>', methods=['POST'])
@login_required
def restock_supply(supply_id):
    if current_user.role not in ['admin', 'producer']:
        return "Acceso denegado", 403
    sup = Supply.query.get_or_404(supply_id)
    add_qty = float(request.form.get('add_qty', 0))
    if add_qty > 0:
        sup.stock += add_qty
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/complete/order/<int:order_id>')
@login_required
def complete_order(order_id):
    if current_user.role not in ['admin', 'employee']:
        return "Acceso denegado", 403
    order = Order.query.get_or_404(order_id)
    if order.status == 'Pendiente':
        order.status = 'Entregado'
        
        fecha_actual = get_colombia_time().strftime('%Y-%m-%d %H:%M:%S')
        new_sale = Sale(
            date_sold=fecha_actual,
            seller=current_user.username,
            client_name=order.client_name,
            total_amount=order.total_amount,
            payment_method=order.payment_type
        )
        db.session.add(new_sale)
        db.session.commit()

        for item in order.items:
            qty = item.quantity
            if item.item_type == 'product':
                prod = Product.query.get(item.item_id)
                if prod:
                    if prod.product_type == 'grande':
                        if item.sale_mode == 'tray':
                            units_to_deduct = qty * prod.tray