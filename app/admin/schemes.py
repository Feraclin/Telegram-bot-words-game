from marshmallow import Schema, fields


class AdminSchema(Schema):
    id = fields.Int(required=False)
    email = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)


class AdminResponseScheme(Schema):
    id = fields.Int(required=True)
    email = fields.Email(required=True)
