import re
import shlex

_NAME=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

def parse_pipeline(text):
    if not isinstance(text,str): raise ValueError('invalid text')
    lexer=shlex.shlex(text,posix=True,punctuation_chars='|')
    lexer.whitespace_split=True; lexer.commenters='#'
    tokens=[piece for token in lexer for piece in ((list(token) if token and set(token) == {'|'} else [token]))]
    stages=[]; current=[]
    for token in tokens + ['|']:
        if token == '|':
            if not current: raise ValueError('empty stage')
            env={}; argv=[]
            for item in current:
                if '=' in item:
                    name,value=item.split('=',1)
                    if not argv:
                        if _NAME.fullmatch(name) is None: raise ValueError('invalid assignment')
                        env[name]=value; continue
                    if _NAME.fullmatch(name): raise ValueError('late assignment')
                argv.append(item)
            if not argv: raise ValueError('missing command')
            stages.append({'env':env,'argv':argv}); current=[]
        else: current.append(token)
    return stages
