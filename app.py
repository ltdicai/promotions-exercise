import sys
import logging
import requests
from cStringIO import StringIO
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, json
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///promotions.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)


class PromotionsParser(object):
    def parse(self, file):
        raise NotImplementedError


class MockParser(PromotionsParser):
    def __init__(self):
        super(MockParser, self).__init__()

    def parse(self, file):
        return [
            {'product_id': 123, 'product_name': 'Teacup',
                'product_description': 'A teacup', 'price': 15.0,
                'discount': 20.0, 'currency': 'USD',
                'shipping_discount': 0.0},
            {'product_id': 124, 'product_name': 'Kid\'s Bicycle',
                'product_description': 'A kids bicycle', 'price': 70.0,
                'discount': 0.0, 'currency': 'USD',
                'shipping_discount': 15.0},
            {'product_id': 125, 'product_name': 'Chair',
                'product_description': 'A comfy chair', 'price': 20.0,
                'discount': 10.0, 'currency': 'USD',
                'shipping_discount': 0.0}]


class JSONPromotionsParser(PromotionsParser):
    def parse(self, file):
        return json.load(file)


PARSERS = {
    'csv': MockParser(),
    'xls': MockParser(),
    'json': JSONPromotionsParser()
}


@app.route('/')
def index():
    try:
        products = Product.query.all()
        return render_template('index.html', products=products)
    except Exception as exc:
        logging.error("Error occurred", exc_info=True)
        if not app.config['DEBUG']:
            return render_template('error.html')
        raise exc


@app.route('/clear')
def clear_db():
    db.session.execute('delete from product')
    db.session.execute('delete from promotion')
    db.session.commit()
    return redirect('/')


@app.route('/promotions', methods=['GET'])
def get_promotions():
    try:
        promotions = Promotion.query.all()
        if 'json' in request.args:
            return jsonify(map(
                lambda promotion: promotion.to_dict(), promotions))
        return render_template('promotions.html', promotions=promotions)
    except Exception as exc:
        logging.error("Error occurred", exc_info=True)
        if not app.config['DEBUG']:
            return render_template('error.html')
        raise exc


@app.route('/promotions/upload', methods=['GET', 'POST'])
def upload_promotions():
    try:
        if request.method == 'POST':
            if 'file' in request.files:
                promotions_file = request.files['file']
                load_promotions_file(promotions_file)
                return redirect('/promotions')
            else:
                params = json.loads(request.data)
                if 'fileURL' not in params:
                    return jsonify(
                        {"status": "error",
                            "message": "missing fileURL"}), 500
                if 'fileType' not in params:
                    return jsonify(
                        {"status": "error",
                            "message": "missing fileType"}), 500
                file_URL = params['fileURL']
                file_type = params['file_type']
                res = requests.get(file_URL, timeout=5)
                if res.status_code == 200 and res.content:
                    file = StringIO(res.content)
                    load_promotions_file(
                        file, extension=file_type)
                    return redirect('/promotions')
                else:
                    raise Exception('Couldn\'t download file')

        else:
            return render_template('upload-promotions.html')
    except Exception as exc:
        logging.error("Error occurred", exc_info=True)
        if not app.config['DEBUG']:
            return render_template('error.html')
        raise exc


def load_promotions_file(file, extension=None):
    '''
    Load each entry in `file` to DB'''
    parser = get_parser_for(file, extension)
    for entry in parser.parse(file):
        try:
            product = Product.query.filter(
                Product.id == entry['product_id']).one_or_none()
            if product is None:
                product = Product(
                    id=entry['product_id'],
                    name=entry['product_name'],
                    description=entry.get('product_description', ''),
                    price=entry['price'])
            promotion = Promotion(
                discount=entry.get('discount'),
                shipping_discount=entry.get('shipping_discount'),
                valid_from=entry.get('valid_from', datetime.utcnow()),
                valid_until=entry.get('valid_until', None),
                product=product)
            if (promotion.discount, promotion.shipping_discount) == (0.0, 0.0):
                raise Exception('Promotion does not have a valid discount')
            db.session.add(promotion)
            db.session.commit()
        except Exception as exc:
            logging.warn("Couldn\'t load promotion for entry %s " % repr(entry))


def get_parser_for(file, extension=None):
    '''
    Lookup in PARSERS for corresponding parser'''
    try:
        extension = extension or file.filename.split('.')[1]
    except IndexError:
        raise Exception('Unknown file type')
    try:
        return PARSERS[extension]
    except KeyError:
        raise Exception('Unavailable parser for %s' % extension)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, default='')
    price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String, default='USD')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'currency': self.currency
        }


class Promotion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discount = db.Column(db.Float, default=0)
    shipping_discount = db.Column(db.Float, default=0)
    valid_from = db.Column(db.Date)
    valid_until = db.Column(db.Date)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'),
                           nullable=False)

    product = db.relationship('Product', backref=db.backref('promotions'))

    def to_dict(self):
        return {
            'discount': self.discount,
            'shipping_discount': self.shipping_discount,
            'valid_from': self.valid_from,
            'valid_until': self.valid_until,
            'product': self.product.to_dict()
        }


db.create_all()


if __name__ == '__main__':
    if 'rebuild' in sys.argv:
        db.session.execute('drop table if exists promotion')
        db.session.execute('drop table if exists product')
        db.session.commit()
        sys.exit()
    app.run(debug=True)
