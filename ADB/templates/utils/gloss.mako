<%page args="primary_text, analyzed_word=[], gloss=[], translated_text='', position=[], grammatical=True"/>

<%
def selected_indicator(size: int, position):
    selected = [False] * size
    positions = [position] if isinstance(position, str) else position
    for pos in positions or []:
        if pos.isnumeric():
            index = int(pos) - 1
            if 0 <= index < size:
                selected[index] = True
        else:
            start, end = pos.split(':')
            start = max(int(start) - 1, 0)
            end = min(int(end), size)
            selected[start:end] = [True] * (end - start)
    return selected

def upper(string: str):
    return string.upper()

words = analyzed_word.split('\t') if analyzed_word else []
glosses = gloss.split('\t') if gloss else []
selected_words = selected_indicator(len(glosses), position)
%>

<%def name="glossed_word(analyzed_word, gloss, selected=False)">
% if selected:
<div style="float: left; margin-bottom: 0.3em;margin-right: 1em;font-weight: bold;">
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
% for word, gl, selected in zip(words, glosses, selected_words):
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
