import os
from flask import Flask, request, jsonify, abort, redirect, url_for
from sqlalchemy import exc, func
import json
from flask_cors import CORS

from .database.models import db_drop_and_create_all, setup_db, Drink
from .auth.auth import AuthError, requires_auth
import logging
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
setup_db(app)
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(filename="api.log", level=logging.ERROR)

#Check drink attribute for create and update
def check_drink_attribute(data):
    # Check drink attributes
    if not data.get('title') or not data.get('recipe') \
            or type(data.get('recipe')) != list:
        abort(422)

    # Check recipe attributes
    for r in data.get('recipe'):
        if not r.get('name') or not r.get('parts') or not r.get('color'):
            abort(422)

@app.after_request
def after_request(response):
    """Modify response headers including Access-Control-* headers.

    :param response: An instance of the response object.
    :return: As instance of the response object with Access-Control-* headers.
    """
    response.headers.add(
        "Access-Control-Allow-Headers", "Content-Type, Authorization"
    )
    response.headers.add(
        "Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS"
    )
    return response

'''
Initialize the datbase on the first run
!! NOTE THIS WILL DROP ALL RECORDS AND START YOUR DB FROM SCRATCH
!! NOTE THIS MUST BE UNCOMMENTED ON FIRST RUN
'''
db_drop_and_create_all()

## ROUTES

@app.route("/drinks", methods=['GET'])
def get_drinks():
    '''
        GET /drinks
            it should be a public endpoint
            it should contain only the drink.short() data representation
        returns status code 200 and json {"success": True, "drinks": drinks} where drinks is the list of drinks
            or appropriate status code indicating reason for failure
    ''' 
    try:
        drinks = Drink.query.all()
        drinks_short = [drink.short() for drink in drinks]
        return jsonify({"sucess":True,"drinks":drinks_short})
    
    except Exception as e:
        logging.exception(e)
        abort(500)
    

    
@app.route("/drinks-detail", methods=['GET'])
@requires_auth("get:drinks-detail")
def get_drinks_detail(payload):
    '''
        GET /drinks-detail
            it should require the 'get:drinks-detail' permission
            it should contain the drink.long() data representation
        returns status code 200 and json {"success": True, "drinks": drinks} where drinks is the list of drinks
            or appropriate status code indicating reason for failure
    '''
    try:
        drinks = Drink.query.all()
        drinks_long = [drink.long() for drink in drinks]
        return jsonify({"sucess":True,"drinks":drinks_long})
    
    except Exception as e:
        logging.exception(e)
        abort(500)

@app.route("/drinks", methods=["POST"])
@requires_auth("post:drinks")
def post_drink(payload):
    '''
        Create a new row in the drinks table
        Require the 'post:drinks' permission
        Contain the drink.long() data representation
        
        returns status code 200 and json {"success": True, "drinks": drink} 
        where drink an array containing only the newly created drink
            or appropriate status code indicating reason for failure
    '''
    data = request.get_json()

    # Check drink attributes
    check_drink_attribute(data)

    # Check drink title 
    drink = Drink.query.filter(
        func.lower(Drink.title) == func.lower(data.get('title'))
    ).one_or_none()

    if drink:
        abort(422)

    try:
        new_drink = Drink(
            title=data.get("title"),
            recipe=json.dumps(data.get("recipe"))
            )

        new_drink.insert()

        return jsonify({"success": True, "drinks": [new_drink.short()],})

    
    except Exception as e:
        logging.exception(e)
        abort(400)

@app.route("/drinks/<int:drink_id>", methods=["PATCH"])
@requires_auth("patch:drinks")
def patch_drink(payload, drink_id):
    '''
        PATCH /drinks/<id>
            <id> is the existing model id
            Respond with a 404 error if <id> is not found
            Update the corresponding row for <id>
            Require the 'patch:drinks' permission
            Contain the drink.long() data representation
        
        returns status code 200 and json {"success": True, "drinks": drink} 
        where drink an array containing only the updated drink
            or appropriate status code indicating reason for failure
    '''
    data = request.get_json()
    drink = Drink.query.filter(
        Drink.id == drink_id
    ).one_or_none()

    if drink is None:
        abort(404)

    # Check drink attributes
    check_drink_attribute(data)
    
    try:
        # update drink
        drink.title = data.get('title')
        drink.recipe = json.dumps(data.get('recipe'))
        drink.update()

        return get_drinks()

    except Exception:
        abort(400)


@app.route("/drinks/<int:drink_id>", methods=["DELETE"])
@requires_auth("delete:drinks")
def delete_drink(payload, drink_id):
    '''
        DELETE /drinks/<id>
            <id> is the existing model id
            Respond with a 404 error if <id> is not found
            Delete the corresponding row for <id>
            Require the 'delete:drinks' permission
        returns status code 200 and json {"success": True, "delete": id} where id is the id of the deleted record
            or appropriate status code indicating reason for failure
    '''
    try:
        drink = Drink.query.get_or_404(drink_id)
        drink.delete()
        return jsonify({"success": True, "delete": drink_id})
    
    except Exception as e:
        logging.exception(e)
        abort(500)


## Error Handling
'''
Implement error handlers using the @app.errorhandler(error) decorator
    each error handler should return (with approprate messages):
             jsonify({
                    "success": False, 
                    "error": 404,
                    "message": "resource not found"
                    }), 404

'''
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "success": False,
        "error": 400,
        "message": "Bad Request"
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "success": False,
        "error": 401,
        "message": "Unauthorized"
    }), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({
        "success": False,
        "error": 403,
        "message": "Forbidden"
    }), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": 404,
        "message": "Resource not found"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "success": False,
        "error": 405,
        "message": "Method not allowed"
    }), 405

@app.errorhandler(422)
def unprocessable(error):
    return jsonify({
        "success": False,
        "error": 422,
        "message": "Unprocessable"
    }), 422

@app.errorhandler(500)
def unknown(error):
    return jsonify({
        "success": False,
        "error": 500,
        "message": "Unknown server error"
    }), 500

'''
Implement error handler for AuthError
    error handler should conform to general task above 
'''
@app.errorhandler(AuthError)
def auth_error(error):
    return jsonify({
        "success": False,
        "error": error.status_code,
        "error_code": error.error.get('code'),
        "message": error.error.get('description')
    }), error.status_code

if __name__ == "__main__":
    app.run(
        debug=True,
        use_debugger=False,
        use_reloader=False,
        passthrough_errors=True,
    )