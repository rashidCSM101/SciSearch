from flask import Flask
from flask_serverless import FlaskServerless
from app_with_spell_correction import app

handler = FlaskServerless(app)
