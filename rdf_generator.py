import csv, datetime, random, re, sqlite3, sys, unidecode
from difflib import SequenceMatcher
from ordinance import Ordinance, OrdinanceDAO
from rdflib import Namespace, Graph, Literal, URIRef, BNode
from rdflib.namespace import DCTERMS, FOAF, OWL, RDF, RDFS, SKOS, XSD

class SearchTerm:
    def __init__ (self, description, keywords):
        self.description = description
        self.keywords = keywords

with open('files/public_servants.csv', newline='') as f:
    reader = csv.DictReader(f)
    reader = list(reader)

def get_random_hash():
    return '%03x' % random.getrandbits(128)

def normalize(content):
    content = content.lower()
    header = content[:content.find('portaria')]
    content = content.replace(header, '').strip()
    title = content.splitlines()[0] + '\n'
    content =  title + content.replace(title, '')
    content = re.sub('\nport[\w\s.]+[\d/]+[\s-]+[\w/]+[|\s]+pág[\w\s]+\d\sde\s\d', '', content).strip()

    return content

def get_title(content):
    content = normalize(content)
    title = content.splitlines()[0]
    title = re.sub('\s+', ' ', re.sub('[,]', ' ', re.sub('[.\']', '', title)))
    return title

def get_number(content):
    title = get_title(content)
    try:
        return int(re.search('\d+', title).group())
    except AttributeError:
        return None

def get_date_published(content):
    title = get_title(content)
    months = {1:'jan', 2:'fev', 3:'mar', 4:'abr', 5:'mai', 6:'jun', 7:'jul', 8:'ago', 9:'set', 10:'out', 11:'nov', 12:'dez'}
    number = str(get_number(title))
    try:
        date = title[title.find(number) + len(number):].strip()
        day = int(re.search('\d+', date).group())
        month = [k for (k,v) in months.items() if v in date][0]
        year = int(re.findall('\d+', date)[1])
        return datetime.datetime(year, month, day).date()
    except:
        return None

def get_description(content):
    try:
        date = get_date_published(content)
        months = {
            1:'janeiro', 2:'fevereiro', 3:'março', 4:'abril',
            5:'maio', 6:'junho', 7:'julho', 8:'agosto',
            9:'setembro', 10:'outubro', 11:'novembro', 12:'dezembro'}
        return ' '.join(('Portaria nº', str(get_number(content)), 'de',date.strftime('%d'),
            'de', months[int(date.strftime('%m'))], 'de', date.strftime('%Y')))
    except:
        return None

def get_publisher(content):
    organizations = {
        'pró-reitor de administração': 'proadm',
        'pró-reitora de administração': 'proadm',
        'pró-reitor de gestão de pessoas': 'progep',
        'pró-reitora de gestão de pessoas': 'progep',
        'diretor do centro de referência': 'cref',
        'presidente do conselho superior': 'consup',
        'reitor': 'reitoria',
        'bom jesus': 'campus_bom_jesus',
        'cabo frio': 'campus_cabo_frio',
        'cambuci': 'campus_cambuci',
        'campos centro':'campus_centro',
        'campos guarus': 'campus_guarus',
        'itaperuna': 'campus_itaperuna',
        'macaé': 'campus_macae',
        'maricá': 'campus_marica',
        'quissamã': 'campus_quissama',
        'santo antônio de pádua': 'campus_padua',
        'são joão da barra': 'campus_sao_joao'
    }
    content = normalize(content)
    if 'resolve' in content:
        content = content[:content.find('resolve')].replace('\n', ' ')
    if 'considerando' in content:
        content = content[:content.find('considerando')].replace('\n', ' ')
    for organization in organizations:
        if organization in content:
            return organizations[organization]
    return 'iff'

def get_function(content):
    functions = {
        'presidente do conselho superior': 'council_president',
        'o pró-reitor': 'pro_rector',
        'pró-reitora': 'pro_rector',
        'reitor': 'rector',
        'diretor': 'general_director',
        'diretora': 'general_director'
    }
    content = normalize(content)
    if 'resolve' in content:
        content = content[:content.find('resolve')].replace('\n', ' ')
    if 'considerando' in content:
        content = content[:content.find('considerando')].replace('\n', ' ')
    for function in functions:
        if function in content:
            return functions[function]
    return None

def get_issuer(content):
    try:
        content = normalize(content)
        term = 'documento assinado eletronicamente'
        issuers = ('reitor', 'diretor', 'presidente')
        issuer = None
        if term in content:
            content = content[content.find(term):].splitlines()[1].strip()
            for i in issuers:
                if i in content:
                    issuer = re.sub('\W', ' ', content[1:content.find(',')]).strip().title()
        else:
            content = content.splitlines()
            content = list(filter(None, content))
            for i in issuers:
                if i in content[len(content) - 1]:
                    issuer = content[len(content) - 2].strip().title()
        return issuer
    except:
        return None

def get_validated_issuer(content):
    issuer = get_issuer(content)
    if issuer:
        for row in reader:
            if SequenceMatcher(a=issuer.lower(),b=dict(row)['NAME'].lower()).ratio() > 0.9:
                return dict(row)['NAME']
    return None

def get_functional_id(name):
    for row in reader:
        if name == dict(row)['NAME']:
            return dict(row)['ID']
    return None

def get_position(name):
    for row in reader:
        if name == dict(row)['NAME']:
            return re.search('[\w ]+', dict(row)['POSITION']).group().strip()
    return None

def get_conditions(content):
    content = normalize(content)
    content = content.replace('consider ando', 'considerando')
    term1 = 'considerando:'
    term2 = 'resolve'
    if term1 in content and term2 in content:
        if content.find(term1) < content.find(term2):
            content = content[content.find(term1) + len(term1):content.find(term2)].strip()
            if not content.startswith('-'):
                return content.replace('\n', ' ')
            content = content.splitlines()
            index = 0
            for line in content[:]:
                if not line.startswith('-'):
                    content[index - 1] += ' ' + line
                    del content[index]
                else:
                    content[index] = line.replace('-', '', 1).strip().capitalize()
                    index += 1
            return content
    return None

def get_acts(content):
    issuer = get_issuer(content)
    content = normalize(content)
    resolve = re.search('resolve(:)?', content)
    signed = re.search('documento assinado eletronicamente por', content)
    if resolve:
        content = content[resolve.span()[1]:].strip()
        article = re.search('^ar(t)?[\.\,]', content)
        decimal = re.search('^\d+\.\s', content)
        roman = re.search('^[\|il][-\—\s\.]', content)
        search = []
        if article:
            end = re.search('ar(t)?[\.\,].+vigor', content)
            if end:
                content = content[:end.span()[0]].strip()
                considering = re.search('\nconsiderando:', content)
                if considering and resolve.span()[0] < considering.span()[0]:
                    content[:considering.span()[0]]
            elif issuer:
                if signed:
                    content = content[:signed.span()[0]].strip()
                content = content[:unidecode.unidecode(content).rfind(issuer.lower())].strip()
            search.append('^ar(t)?[\.\,]')
            search.append('^ar(t)?[\.\,][^a-z]+')
        elif decimal:
            return 'decimal'
            end = re.search('^\d+\.\s.+vigor', content)
            if end:
                content = content[:end.span()[0]].strip()
                considering = re.search('\nconsiderando:', content)
                if considering and resolve.span()[0] < considering.span()[0]:
                    content[:considering.span()[0]]
            elif issuer:
                if signed:
                    content = content[:signed.span()[0]].strip()
                content = content[:unidecode.unidecode(content).rfind(issuer.lower())].strip()
            search.append('^ar(t)?\.')
            search.append('^ar(t)?\.[^a-z]+')
        elif roman:
            end = re.search('[\|il]+[-\—\s\.]+.+vigor', content)
            if end:
                content = content[:end.span()[0]].strip()
                considering = re.search('\nconsiderando:', content)
                if considering and resolve.span()[0] < considering.span()[0]:
                    content[:considering.span()[0]]
            elif issuer:
                if signed:
                    content = content[:signed.span()[0]].strip()
                content = content[:unidecode.unidecode(content).rfind(issuer.lower())].strip()
            search.append('^[\|il]+[-\—\s\.]')
            search.append('^[\|il]+[-\—\s\.][^a-z]+')
        else:
            if issuer:
                if signed:
                    content = content[:signed.span()[0]].strip()
                content = content[:unidecode.unidecode(content).rfind(unidecode.unidecode(issuer.lower()))].strip()
            return [content.replace('\n', ' ').strip().capitalize()]
        if search:
            content = content.split('\n')
            index = 0
            while index < len(content):
                if not re.search(search[0], content[index]):
                    content[index - 1] += ' ' + content[index]
                    del content[index]
                else:
                    content[index] = re.sub(search[1], '', content[index]).capitalize()
                    index += 1
            return content
    return None

def get_references(act):
    servants = []
    for row in reader:
        if dict(row)['NAME'].lower() in unidecode.unidecode(act).lower():
            servants.append(dict(row)['NAME'])
    return servants

def classify_act(act):
    search_terms = [
        SearchTerm('aceleracao_promocao', ['conceder', 'aceleração', 'promoção', 'classe']),
        SearchTerm('adicional_insalubridade', ['conceder', 'adicional', 'insalubridade']),
        SearchTerm('adicional_periculosidade', ['conceder', 'adicional', 'periculosidade']),
        SearchTerm('afastamento', ['afastamento']),
        SearchTerm('agradecimento', ['agradecer']),
        SearchTerm('alteracao_estrutura_organizacional', ['alterar', 'parcialmente', 'estrutura', 'organizacional']),
        SearchTerm('alteracao_jornada_trabalho', ['alterar', 'jornada', 'trabalho']),
        SearchTerm('ambiente_organizacional', ['homologar', 'ambiente', 'organizacional']),
        SearchTerm('autorizacao_conducao_veiculos', ['autorizar', 'veículo']),
        SearchTerm('avaliacao_estagio_probatorio', ['homologar', 'avaliação', 'estágio', 'probatório']),
        SearchTerm('convocacao', ['convocar', 'concurso', 'público']),
        SearchTerm('designacao_chefia', ['designar', 'ocupar', 'função']),
        SearchTerm('designacao_comissao', ['designar', 'comissão']),
        SearchTerm('designacao_grupo_trabalho', ['designar', 'grupo', 'trabalho']),
        SearchTerm('designacao_grupo_trabalho', ['instituir', 'grupo', 'trabalho']),
        SearchTerm('designacao_fiscal_contratos', ['designar', 'fiscal', 'contrato']),
        SearchTerm('designacao_responsavel_setor', ['designar', 'atuar', 'responsável']),
        SearchTerm('dispensa_chefia', ['dispensar', 'função']),
        SearchTerm('dispensa_responsavel_setor', ['dispensar', 'responsável']),
        SearchTerm('efetivacao_lotacao', ['efetivar', 'unidade', 'administrativa']),
        SearchTerm('exoneracao', ['exonerar']),
        SearchTerm('horario_especial_estudante', ['horário', 'especial', 'estudante']),
        SearchTerm('incentivo_qualificacao', ['conceder', 'incentivo', 'qualificação']),
        SearchTerm('licenca_atividade_politica', ['conceder', 'licença', 'atividade', 'política']),
        SearchTerm('licenca_capacitacao', ['conceder', 'licença', 'capacitação']),
        SearchTerm('licenca_interesse_particular', ['conceder', 'licença', 'interesses', 'particulares']),
        SearchTerm('licenca_premio', ['conceder', 'licença', 'prêmio']),
        SearchTerm('localizacao_ambiente_atuacao', ['localizar', 'ambiente', 'atuação']),
        SearchTerm('nomeacao', ['nomear', 'concurso', 'público']),
        SearchTerm('progressao_capacitacao', ['conceder', 'progressão', 'capacitação']),
        SearchTerm('progressao_desempenho', ['conceder', 'progressão', 'desempenho']),
        SearchTerm('progressao_merito', ['conceder', 'progressão', 'mérito']),
        SearchTerm('promocao_desempenho', ['conceder', 'promoção', 'desempenho']),
        SearchTerm('reconhecimento_saberes_competencias', ['conceder', 'reconhecimento', 'saberes', 'competências']),
        SearchTerm('reducao_jornada_trabalho', ['autorizar', 'alteração', 'jornada', 'trabalho']),
        SearchTerm('nomeacao', ['remover', 'servidor']),
        SearchTerm('retribuicao_titulacao', ['conceder', 'retribuição', 'titulação']),
        SearchTerm('substituicao_chefia', ['designar', 'responder', 'provisoriamente', 'afastamento']),
    ]
    for search_term in search_terms:
        found = True
        for keyword in search_term.keywords:
            if not re.search(keyword, act.lower()):
                found = False
                break
        if found:
            return search_term.description
    return None

def print_info(content):
    print('Número: ' + str(get_number(content)))
    print('Data de Publicação: ' + str(get_date_published(content)))
    print('Ano: ' + str(get_year(content)))
    print('Descrição: ' + str(get_description(content)))
    print('Publicador: ' + str(get_publisher(content)))
    print('Emissor: ' + str(get_validated_issuer(content)))
    print('\tMatrícula: ' + str(get_functional_id(content)))
    print('\tFunção: ' + str(get_function(content)))
    print('\tCargo: ' + str(get_position(content)))
    print('Condições:')
    for condition in get_conditions(content):
        print('- ' + str(condition))
    print('Atos:')
    for act in get_acts(content):
        print('- ' + str(act))
        print('\tTipo: ' + str(classify_act(act)))
        print('\tServidores referenciados: ')
        for reference in get_reference(act):
            print('\t\t' + reference)

def get_rdf_graph(ordinances):
    ORD = Namespace('http://purl.org/ordinance-ontology/')
    SCHEMA = Namespace('http://schema.org/')

    graph = Graph(base='http://purl.org/ordinance-ontology/')
    graph.bind('rdf', RDF)
    graph.bind('foaf', FOAF)
    graph.bind('ord', ORD)
    graph.bind('rdfs', RDFS)
    graph.bind('schema', SCHEMA)
    graph.bind('skos', SKOS)
    graph.bind('xsd', XSD)

    global_count = 1

    for ordinance in ordinances:
        print('Ordinance #' + str(global_count))
        content = dict(ordinance)['content']

        ordinance_description = get_description(content)
        ordinance_publisher = get_publisher(content)
        ordinance_number = get_number(content)
        ordinance_date_published = get_date_published(content)
        ordinance_id = ordinance_publisher + '_' + str(ordinance_date_published) + '_' + str(ordinance_number)
        ordinance_url = dict(ordinance)['url']

        ordinance = URIRef(ordinance_id)

        graph.add((ordinance, RDF.type, ORD.Ordinance))
        graph.add((ordinance, ORD.number, Literal(ordinance_number, datatype=XSD.string)))
        graph.add((ordinance, SCHEMA.datePublished, Literal(ordinance_date_published, datatype=XSD.dateTime)))
        graph.add((ordinance, SCHEMA.description, Literal(ordinance_description, datatype=XSD.string)))
        graph.add((ordinance, ORD.directPublisher, URIRef(ordinance_publisher)))
        graph.add((ordinance, SCHEMA.url, Literal(ordinance_url, datatype=XSD.anyURI)))

        ordinance_issuer = get_validated_issuer(content)
        if ordinance_issuer:
            issuer_position = get_position(ordinance_issuer)
            issuer_function = get_function(content)
            issuer_functional_id = get_functional_id(ordinance_issuer)

            position = URIRef('position_' + get_random_hash())
            graph.add((position, RDF.type, SKOS.Concept))
            graph.add((position, SKOS.prefLabel, Literal(issuer_position, datatype=XSD.string)))

            entailment = URIRef('entailment_' + get_random_hash())
            graph.add((entailment, RDF.type, ORD.Entailment))
            graph.add((entailment, ORD.hasPosition, position))
            graph.add((entailment, ORD.functionalId, Literal(issuer_functional_id, datatype=XSD.string)))


            mandate = URIRef('mandate_' + get_random_hash())
            graph.add((mandate, RDF.type, ORD.Mandate))
            if issuer_function:
                    graph.add((mandate, ORD.hasFunction, URIRef(issuer_function)))

            public_servant_issuer = URIRef('public_servant_' + issuer_functional_id)
            graph.add((public_servant_issuer, RDF.type, ORD.PublicServant))
            graph.add((public_servant_issuer, SCHEMA.name, Literal(ordinance_issuer, datatype=XSD.string)))
            graph.add((public_servant_issuer, ORD.entailedTo, entailment))
            graph.add((public_servant_issuer, ORD.exercises, mandate))

            graph.add((ordinance, ORD.issuedBy, mandate))

        conditions = get_conditions(content)
        if conditions:
            count = 1
            for c in conditions:
                condition = URIRef(ordinance_id + '_condition_' + str(count))
                graph.add((condition, RDF.type, ORD.Condition))
                graph.add((condition, SCHEMA.description, Literal(c, datatype=XSD.string)))
                graph.add((ordinance, ORD.hasCondition, condition))
                count += 1

        acts = get_acts(content)
        if acts:
            count = 1
            for a in acts:
                act = URIRef(ordinance_id + '_act_' + str(count))
                graph.add((act, RDF.type, ORD.Act))
                graph.add((act, SCHEMA.description, Literal(a, datatype=XSD.string)))
                graph.add((ordinance, ORD.hasAct, act))

                act_class = classify_act(a)
                if act_class:
                    graph.add((act, ORD.hasType, URIRef(act_class)))

                names_referenced = get_references(a)
                if names_referenced:
                    for name in names_referenced:
                        functional_id = get_functional_id(name)

                        position = URIRef('position_' + get_random_hash())
                        graph.add((position, RDF.type, SKOS.Concept))
                        graph.add((position, SKOS.prefLabel, Literal(get_position(name), datatype=XSD.string)))

                        entailment = URIRef('entailment_' + get_random_hash())
                        graph.add((entailment, RDF.type, ORD.Entailment))
                        graph.add((entailment, ORD.hasPosition, position))
                        graph.add((entailment, ORD.functionalId, Literal(functional_id, datatype=XSD.string)))

                        public_servant = URIRef('public_servant_' + functional_id)
                        graph.add((public_servant, RDF.type, ORD.PublicServant))
                        graph.add((public_servant, SCHEMA.name, Literal(name, datatype=XSD.string)))
                        graph.add((public_servant, ORD.entailedTo, entailment))

                        reference = URIRef('reference_' + get_random_hash())
                        graph.add((reference, ORD.subject, public_servant))

                        graph.add((act, ORD.references, reference))
                count += 1
        global_count = global_count + 1
    return graph

if __name__ == '__main__':
    ordinances = OrdinanceDAO.get_all()
    amount = len(ordinances)
    position = 0
    number = 1
    while position < amount:
        ords = ordinances[position:position + 100]
        graph = get_rdf_graph(ords)
        f = open('graphs/graph_' + str(number) + '.ttl', 'a')
        f.write(graph.serialize(format='turtle').decode('utf-8'))
        f.close()
        number += 1
        position += 100
