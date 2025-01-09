from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import PrimaryKeyConstraint
import yaml
import os
import json
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database Configuration
connection_string = "mssql+pyodbc://sa:MICROSOFTsucksH4RD@localhost:1433/DD_CU?driver=ODBC+Driver+17+for+SQL+Server"
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.getcwd(), 'tests.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class RuleMaster(db.Model):
    __tablename__ = 'rule_master'
    # __table_args__ = {'schema': 'test_result'}

    id = db.Column(db.Integer, primary_key=True)
    rule_name = db.Column(db.String(255), nullable=False)
    rule_name_in_dbt_expectations = db.Column(db.String(255), nullable=False)


class Rule(db.Model):
    __tablename__ = 'Rule'
    # __table_args__ = {'schema': 'test_result'}

    id = db.Column(db.Integer, primary_key=True)
    rule_name = db.Column(db.String(255), nullable=False)
    table_name = db.Column(db.String(255), nullable=False)
    column_name = db.Column(db.String(255), nullable=False)
    param1 = db.Column(db.String(255), nullable=True)
    value_param1 = db.Column(db.String(255), nullable=True)
    param2 = db.Column(db.String(255), nullable=True)
    value_param2 = db.Column(db.String(255), nullable=True)
    param3 = db.Column(db.String(255), nullable=True)
    value_param3 = db.Column(db.String(255), nullable=True)
    param4 = db.Column(db.String(255), nullable=True)
    value_param4 = db.Column(db.String(255), nullable=True)
    param5 = db.Column(db.String(255), nullable=True)
    value_param5 = db.Column(db.String(255), nullable=True)


def fetch_tables_and_columns():
    with open("template_schema.yml", 'r', encoding='utf-8') as f:
        file_config = next(yaml.safe_load_all(f.read()))
    tablesDict = {}
    for table in file_config['sources'][0]['tables']:
        tablesDict[table['name']] = []
        for column in table['columns']:
            tablesDict[table['name']].append(column['name'])
    return tablesDict


TABLESDICT = fetch_tables_and_columns()


def try_parse_date(value):
    date_regex = r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"
    if isinstance(value, str):
        if value == "current date":
            return "CAST('{{ run_started_at.strftime('%Y-%m-%d') }}' AS DATE)"
        elif bool(re.match(date_regex, value)):
            return f"CAST('{value}' AS DATE)"
        else:
            return value
    else:
        return value


def try_parse_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return value


# Initialize the database
with app.app_context():
    db.create_all()



@app.route('/', methods=['GET'])
def index():
    RuleMaster.query.delete()
    RULE_MASTERS = [
    RuleMaster(
        id=0,
        rule_name="not_null",
        rule_name_in_dbt_expectations="not_null"
    ),
    RuleMaster(
        id=1,
        rule_name='between',
        rule_name_in_dbt_expectations='dbt_expectations.expect_column_values_to_be_between'
    ),
    RuleMaster(
        id=2,
        rule_name='accepted_values',
        rule_name_in_dbt_expectations='accepted_values'
    )]
    db.session.add_all(RULE_MASTERS)
    db.session.commit()
    tablesDict = fetch_tables_and_columns()
    tableNames = list(tablesDict.keys())

    # Query existing rules
    existing_rules = Rule.query.all()
    rule_names = [item.rule_name for item in RuleMaster.query.all()]
    rules = {name: [] for name in rule_names}

    for rule in existing_rules:
        rules[rule.rule_name].append({
            "id": rule.id,
            "table": rule.table_name,
            "column": rule.column_name,
            "param1": rule.param1,
            "value_param1": json.loads(rule.value_param1) if rule.value_param1 else None,
            "param2": rule.param2,
            "value_param2": json.loads(rule.value_param2) if rule.value_param2 else None,
            "param3": rule.param3,
            "value_param3": json.loads(rule.value_param3) if rule.value_param3 else None,
            "param4": rule.param4,
            "value_param4": json.loads(rule.value_param4) if rule.value_param4 else None,
            "param5": rule.param5,
            "value_param5": json.loads(rule.value_param5) if rule.value_param5 else None
        })
    return render_template(
        'rule_form.html',
        rules=rules,
        rule_names=rule_names,
        tablesDict=tablesDict,
        tableNames=tableNames,
        table_name="",
        existing_rules=len(existing_rules)
    )

@app.route('/save_rules', methods=['POST'])
def save_rules():
    try:
        rules = request.json.get('rules', [])
        if not rules:
            return jsonify({"status": "error", "message": "No rules provided!"}), 400
        # Save new rules
        for rule in rules:
            print(rule['value_param1'])
            new_rule = Rule(
                rule_name=rule['ruleName'],
                table_name=rule['tableName'],
                column_name=rule['columnName'],
                param1=rule['param1'],
                value_param1=json.dumps(rule['value_param1']) if rule['value_param1']!=None else None,
                param2=rule['param2'],
                value_param2=json.dumps(rule['value_param2']) if rule['value_param2']!=None else None,
                param3=rule['param3'],
                value_param3=json.dumps(rule['value_param3']) if rule['value_param3']!=None else None,
                param4=rule['param4'],
                value_param4=json.dumps(rule['value_param4']) if rule['value_param4']!=None else None,
                param5=rule['param5'],
                value_param5=json.dumps(rule['value_param5']) if rule['value_param5']!=None else None,
            )
            print(new_rule.value_param1)
            db.session.add(new_rule)
        db.session.commit()

        return jsonify({"status": "success", "message": "Rules saved successfully!"})
    except Exception as e:
        print(e)
        db.session.rollback()
        print(f"Error saving rules: {e}")
        return jsonify({"status": "error", "message": "An error occurred while saving rules."}), 500


@app.route('/remove_rules', methods=['POST'])
def remove_rules():
    try:
        remove_rules = request.json.get('removedRulesId', [])
        if remove_rules == []:
            return jsonify({"status": "success", "message": "No rules removed!"})

        # Save new rules
        for rule_id in remove_rules:
            Rule.query.filter_by(id=rule_id).delete()
        db.session.commit()
        return jsonify({"status": "success", "message": "Rules removed successfully!"})
    except Exception as e:
        print(e)
        db.session.rollback()
        print(f"Error saving rules: {e}")
        return jsonify({"status": "error", "message": "An error occurred while saving rules."}), 500

@app.route('/get_columns/<table_name>', methods=['GET'])
def get_columns(table_name):
    return jsonify(TABLESDICT[table_name])

@app.route('/get_rule_names', methods=['GET'])
def get_rule_names():
    rule_names = [item.rule_name for item in RuleMaster.query.all()]
    return jsonify(rule_names)

@app.route('/create_config_file', methods=['GET'])
def create_config_file():
    rules_master = RuleMaster.query.all()
    master_dict = {item.rule_name: item.rule_name_in_dbt_expectations for item in rules_master}
    for item in rules_master:
        print(item)
    with open("template_schema.yml", 'r', encoding='utf-8') as f:
        file_config = next(yaml.safe_load_all(f.read()))
    rules_dict = {}
    for rule in Rule.query.all():
        try:
            rules_dict[rule.table_name.upper()]
        except KeyError:
            rules_dict[rule.table_name.upper()] = {}

        
        if rule.param1 or rule.param2 or rule.param3 or rule.param4 or rule.param5:
            # print(json.loads(rule.value_param1))
            _ = {
            master_dict[rule.rule_name]: {
                    **{
                        param: try_parse_date(json.loads(value or 'null'))
                        for param, value in {
                            rule.param1: rule.value_param1,
                            rule.param2: rule.value_param2,
                            rule.param3: rule.value_param3,
                            rule.param4: rule.value_param4,
                            rule.param5: rule.value_param5,
                        }.items()
                        if param  # Include only if param is not None
                        },
                    }
            }
        else:
                _ = master_dict[rule.rule_name]

        try:
            rules_dict[rule.table_name.upper()][rule.column_name.upper()]['data_tests'].append(_)
        except KeyError:
            rules_dict[rule.table_name.upper()][rule.column_name.upper()] = {'data_tests': []}
            rules_dict[rule.table_name.upper()][rule.column_name.upper()]['data_tests'].append(_)
        except Exception as e:
            print(e)

    for table in file_config['sources'][0]['tables']:
        try:
            rules_dict[table['name']]
            for column in table['columns']:
                try:
                    column['data_tests'] = rules_dict[table['name']][column['name']]['data_tests']
                except KeyError:
                    pass
        except KeyError:
            pass

    with open(r'schema.yml', "w", encoding="utf-8") as f:
        yaml.dump(file_config, f, allow_unicode=True)

    return jsonify({"status": "success", "message": "Schema wrote!"})

if __name__ == '__main__':
    app.run(debug=True)
