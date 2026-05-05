<%page args="primary_text, analyzed_word=[], gloss=[], translated_text='', position=[], grammatical=True"/>

<%
def selected_indicator(size: int, position: list):
    selected = [False] * size
    for pos in position:
        if pos.isnumeric(): selected[int(pos)-1] = True
        else:
            start, end = pos.split(':')
            selected[int(start)-1:int(end)] = True
    return selected

def upper(string: str):
    return string.upper()
%>

<%def name="glossed_word(analyzed_word, gloss, selected=False)">
% if selected:
<div style="float: left; margin-bottom: 0.3em;margin-right: 1em;font-style: bold;">
% else:
<div style="float: left; margin-bottom: 0.3em;margin-right: 1em;">
% endif
    % if analyzed_word is not None:
    <p style="margin: 0px;font-style: italic;">${analyzed_word}</p>
    % endif
    % if gloss is not None:
    <p style="margin: 0px;">
% for (i, morpheme) in enumerate(gloss.split('-')):
% if i > 0:
<span>-</span>\
% endif
% if upper(morpheme) == morpheme:
<span style="font-variant: small-caps; font-variant-numeric: lining-nums; text-transform: lowercase;">${morpheme}</span>\
% else:
${morpheme}\
% endif
% endfor
    </p>
    % endif
</div>
</%def>

<div class="gloss">
    <p style="margin-bottom: 0.3em;">${'*' if not grammatical else ''}${primary_text}</p>
% if not grammatical:
    <div style="float: left;">*</div>
% endif
% for word, gl, selected in zip(analyzed_word.split('\t'), gloss.split('\t'), selected_indicator(len(gloss), position)):
${glossed_word(word, gl, selected)}
% endfor
% if translated_text is not None:
    % if grammatical:
    <p style="clear: left;">${translated_text}</p>
    % else:
    <p style="clear: left;">Ожидаемое значение: ${translated_text}</p>
    % endif
% endif
    <div style="clear: left; display: block;"></div>
</div>