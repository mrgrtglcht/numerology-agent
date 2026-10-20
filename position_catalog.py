"""All 32 bot positions: exact domains, geometry and bounded interpretation scope."""
from matrix_rules import domains,THEMES

BASE='https://axvii.ru/blog/'
GENERAL=BASE+'kak-chitat-matritsu-sudby'
CALC=BASE+'kak-rasschitat-matritsu-sudby-samomu'
AXES={'A':('левый','семейный опыт','family'), 'C':('верхний','таланты','talent'),
 'E':('правый','дела и ресурсы','work'), 'G':('нижний','кармический хвост','tail'),
 'B':('верхний левый','мужская родовая линия','family'),
 'F':('нижний правый','мужская родовая линия','family'),
 'D':('верхний правый','женская родовая линия','family'),
 'H':('нижний левый','женская родовая линия','family')}

def catalog():
    formulas={'A':'reduce22(day)','C':'month','E':'reduce22(sum(year digits))',
      'G':'r(A+C+E)','I':'r(A+C+E+G)','B':'r(A+C)','D':'r(C+E)','F':'r(E+G)','H':'r(G+A)',
      'I1':'r(B+D+F+H)','I2':'r(I+I1)','F3':'r(G2+E2)','FL':'r(G2+F3)','FR':'r(E2+F3)',
      'A3':'r(A2+I)','C3':'r(C2+I)'}
    result={}
    for key,(direction,meaning,group) in AXES.items():
        for suffix,location in (('', 'внешняя'),('1','средняя'),('2','внутренняя')):
            code=key+suffix
            if suffix:formulas[code]=f'r({key}+'+('I)' if suffix=='2' else key+'2)')
            result[code]={'id':code,'label':f'{location} точка: {direction} луч',
              'meaning':meaning,'group':group,'instruction':f'найди {direction} луч. нужна его {location} точка.',
              'interpretation_status':'axis_context','source':GENERAL}
    result.update({
      'I':{'label':'центр личной матрицы','meaning':'привычный способ действовать и личная опора','group':'character',
           'instruction':'найди большой круг в центре личной матрицы.','source':GENERAL,'interpretation_status':'verified'},
      'I1':{'label':'центр рода','meaning':'расчётный центр диагоналей по формулам бота','group':'technical'},
      'I2':{'label':'дополнительная точка правее центра','meaning':'сумма центра и центра рода','group':'technical'},
      'A3':{'label':'дополнительная точка слева от центра','meaning':'сумма A2 и I','group':'technical'},
      'C3':{'label':'дополнительная точка выше центра','meaning':'сумма C2 и I','group':'technical'},
      'FL':{'label':'точка под знаком сердца','meaning':'качества взаимодействия в отношениях','group':'love',
            'instruction':THEMES['partner']['instruction'],'source':THEMES['partner']['source'],'interpretation_status':'verified'},
      'FR':{'label':'точка под знаком денег','meaning':'рабочие задачи и способы реализации','group':'work',
            'instruction':THEMES['profession']['instruction'],'source':THEMES['profession']['source'],'interpretation_status':'verified'},
      'F3':{'label':'пересечение каналов отношений и денег','meaning':'совместное чтение тем отношений и ресурсов','group':'channels',
            'instruction':'найди среднюю точку диагонали, соединяющей внутренние точки нижнего и правого лучей.',
            'source':THEMES['profession']['source'],'interpretation_status':'verified'}
    })
    # The broad axis is supported; individual psychological labels are not silently invented.
    result['C']['meaning']='внешняя точка талантов (месяц рождения)'
    result['C1']['meaning']='интеллектуальный талант'
    result['C2']['meaning']='самовыражение'
    for code,item in result.items():
        item.update(id=code,formula=formulas[code],allowed=domains()['positions'][code],method=domains()['method'])
        item.setdefault('source',CALC);item.setdefault('instruction','найди отмеченную точку на схеме.')
        item.setdefault('interpretation_status','technical_only')
        # Family axes and tail combinations require a dedicated combined reading; no invented one-point diagnoses.
        item['auto_topic_enabled']=item['group'] in ('character','talent','love','work')
    assert set(result)==set(domains()['positions'])
    return result

