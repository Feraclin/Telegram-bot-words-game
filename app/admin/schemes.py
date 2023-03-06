from hashlib import sha256

from marshmallow import Schema, fields, pre_load


class AdminSchema(Schema):
    id = fields.Int(dump_only=True)
    email = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)

    @pre_load
    def hash_password(self, data: dict, **kwargs) -> dict:
        data["password"] = sha256(data["password"].encode()).hexdigest()
        return data


class AdminResponseScheme(Schema):
    id = fields.Int(required=True)
    email = fields.Email(required=True)
