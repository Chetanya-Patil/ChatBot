import sqlite3

def connect(*k, **p):
    p['detect_types']=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES
    return sqlite3.connect( *k, **p)

def sqlite3UnicodeFetch(encoding):
    def sqlite3UnicodeFetch_converter(conversion, state=None):
        """\

        Convert the results of a cursor fetch to the correct format.
    
        The ``conversion.value.cursor.description`` argument contains
        information about each value returned in the form of a 7-item tuple:
        ``(name, type_code, display_size, internal_size, precision, scale,
        null_ok)``. The ``.description`` attribute will be ``None`` for
        operations which do not return rows.
    
        The ``type_code`` will be different for each driver.

        """
        cursor = conversion.value.cursor
        rows = conversion.value.result
    
        if cursor.description is None:
            conversion.result = rows
        else:
            new_rows = []
            for row in rows:
                new_row = []
                for i, value in enumerate(row):
                    if 0:#value is not None and cursor.description[i][1] == sqlite3.STRING:
                        new_row.append(value.decode(encoding))
                    else:
                        new_row.append(value)
                new_rows.append(tuple(new_row))
            conversion.result = tuple(new_rows)
    return sqlite3UnicodeFetch_converter

sqlite3_utf8_fetch = sqlite3UnicodeFetch('utf8')

def insert_record(
    connection, 
    table_name, 
    data_dict, 
    primary_key_column_name=None,
    database=None,
):
    """\
    Implementation of ``insert_record()`` for SQLite3. See 
    ``insert_record()`` for details.
    """
    cursor = connection.cursor()
    columns = []
    values = []
    for k, v in data_dict.items():
        values.append(v)
        columns.append(k)
    values_str = ""
    for value in values:
        values_str += "?, "
    values_str = values_str[:-2]

    if primary_key_column_name and data_dict.has_key(primary_key_column_name):
        raise Exception(
            "You shouldn't specify the primary key in the data_dict, "
            "the new value will be returned automatically if you specify "
            "primary_key_column_name"
        )
    sql = """
        INSERT INTO %s (%s) VALUES (%s);
    """ % (
        table_name,
        ', '.join(['"%s"'%col for col in columns]),
        values_str
    )
    cursor.execute(sql, tuple(values))
    if primary_key_column_name is not None:
        cursor.execute('SELECT last_insert_rowid() as last_insert_rowid')
        uid = cursor.fetchall()[0][0]
    cursor.close()
    if primary_key_column_name is not None:
        return uid
    return None
 
def update_config(bag, name, config):
    if config.get('pool', False):
        raise Exception('The %s.pool option must be False for SQLite3'%name)
    from configconvert import handle_option_error, handle_section_error
    if not bag.app.option.has_key(name):
        raise handle_section_error(
            bag, 
            name, 
            (
                "'%s.database' and '%s.plugin' (the module module and "
                "function to use to create a connection)"%(name, name)
            )
        )
    from stringconvert import unicodeToUnicode, unicodeToInteger,\
       unicodeToBoolean
    from recordconvert import toRecord
    from configconvert import stringToObject
    from conversionkit import Conversion, chainConverters

    # Re-use the converters   
    unicode_to_integer = unicodeToInteger()
    null = unicodeToUnicode()

    database_config = toRecord(
        missing_defaults=dict(
            creator=connect,
            fetch_converter=sqlite3_utf8_fetch,
            execute_converter=None,
        ),
        missing_or_empty_errors = dict(
            database="The required option '%s.database' is missing"%(name,),
        ),
        converters=dict(
            database = null,
            creator = stringToObject(),
            fetch_converter = stringToObject(),
            execute_converter = stringToObject(),
        ),
    ) 
    conversion = Conversion(bag.app.option[name]).perform(database_config)
    if not conversion.successful:
        handle_option_error(conversion, name)
    else:
        config = conversion.result
    return config
 
