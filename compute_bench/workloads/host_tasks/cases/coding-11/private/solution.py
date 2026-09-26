import math

_DEFAULTS = {'timeout':5.0,'retries':3,'enabled':True,'tags':[]}

def resolve_settings(layers):
    result = {'timeout':5.0,'retries':3,'enabled':True,'tags':[]}
    for layer in layers:
        if not isinstance(layer, dict) or set(layer) - set(_DEFAULTS):
            raise ValueError('invalid layer')
        for key, value in layer.items():
            if value is None:
                result[key] = list(_DEFAULTS[key]) if key == 'tags' else _DEFAULTS[key]
            elif key == 'timeout':
                if isinstance(value, bool): raise ValueError('invalid timeout')
                try: parsed = float(value)
                except (TypeError, ValueError): raise ValueError('invalid timeout')
                if not math.isfinite(parsed) or parsed <= 0: raise ValueError('invalid timeout')
                result[key] = parsed
            elif key == 'retries':
                if isinstance(value, bool) or (isinstance(value, str) and not value.strip().isdigit()): raise ValueError('invalid retries')
                try: parsed = int(value)
                except (TypeError, ValueError): raise ValueError('invalid retries')
                if parsed < 0 or isinstance(value, float) and not value.is_integer(): raise ValueError('invalid retries')
                result[key] = parsed
            elif key == 'enabled':
                if isinstance(value, bool): result[key] = value
                elif isinstance(value, str) and value.strip().lower() in {'true','yes','on','1','false','no','off','0'}:
                    result[key] = value.strip().lower() in {'true','yes','on','1'}
                else: raise ValueError('invalid enabled')
            else:
                try: values = value.split(',') if isinstance(value, str) else list(value)
                except TypeError: raise ValueError('invalid tags')
                tags = []
                for item in values:
                    if not isinstance(item, str): raise ValueError('invalid tag')
                    item = item.strip()
                    if item and item not in tags: tags.append(item)
                result[key] = tags
    return result
