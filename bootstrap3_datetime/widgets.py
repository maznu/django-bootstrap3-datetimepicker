# -*- coding: utf-8 -*-
from django.forms.utils import flatatt
from django.forms.widgets import DateTimeInput
from django.utils import translation
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape

try:
    import json
except ImportError:
    from django.utils import simplejson as json
try:
    from django.utils.encoding import force_unicode as force_text
except ImportError:  # python3
    from django.utils.encoding import force_text


def get_momentjs_supported_locale():
    # List of moment.js supported locales:
    # https://github.com/moment/moment/blob/develop/component.json

    # List of django supported languages:
    # from django.conf.locale import LANG_INFO
    # print(list(LANG_INFO.keys()))

    # Get the language code
    lang = translation.get_language()
    if lang is None:
        return
    lang = lang.lower()
    if lang in ('en', 'en-us'):
        return

    # These are known langs which don't supported by moment.js (while supported by
    # Django. Use contrib/get_fallback_and_unsupported_locale_name.py to generate
    # this list
    not_supported_list = [
        'ast', 'dsb', 'ga', 'hsb', 'ia', 'io', 'mn', 'no',
        'os', 'pa', 'sr-latn', 'tt', 'udm']
    if lang in not_supported_list:
        return

    known_fallbacks = {
        # For Chinese
        'zh-hans': "zh-cn",
        'zh-my': "zh-cn",
        'zh-sg': "zh-cn",
        'zh-hant': "zh-tw",  # or 'zh-hk'
        'zh-mo': "zh-tw",

        # For Spanish
        'es-ar': "es",
        'es-co': "es",
        'es-mx': "es",
        'es-ni': "es",
        'es-ve': "es",
    }

    return known_fallbacks.get(lang) or lang


class DateTimePicker(DateTimeInput):
    class Media:
        js = ('bootstrap3_datetime/js/moment-with-locales.min.js',
              'bootstrap3_datetime/js/bootstrap-datetimepicker.min.js')
        css = {'all': ('bootstrap3_datetime/css/bootstrap-datetimepicker.min.css',), }

    # http://momentjs.com/docs/#/parsing/string-format/
    # http://docs.python.org/2/library/datetime.html#strftime-strptime-behavior
    format_map = (('DDD', r'%j'),
                  ('DD', r'%d'),
                  ('MMMM', r'%B'),
                  ('MMM', r'%b'),
                  ('MM', r'%m'),
                  ('YYYY', r'%Y'),
                  ('YY', r'%y'),
                  ('HH', r'%H'),
                  ('hh', r'%I'),
                  ('mm', r'%M'),
                  ('ss', r'%S'),
                  ('a', r'%p'),
                  ('ZZ', r'%z'),
    )

    @classmethod
    def conv_datetime_format_py2js(cls, format):
        for js, py in cls.format_map:
            format = format.replace(py, js)
        return format

    @classmethod
    def conv_datetime_format_js2py(cls, format):
        for js, py in cls.format_map:
            format = format.replace(js, py)
        return format

    html_template = '''
        <div%(div_attrs)s>
            <input%(input_attrs)s/>
            <span class="input-group-addon">
                <span%(icon_attrs)s></span>
            </span>
        </div>'''

    js_template = '''
        <script>
            (function(window) {
                var callback = function() {
                    $(function(){$("#%(picker_id)s:has(input:not([readonly],[disabled]))").datetimepicker(%(options)s);});
                };
                // if window object id loaded already, call directly callback function
                if (-1 != $.inArray(
                        document.readyState,
                        ["loaded", "interactive", "complete"]
                    )
                ) {
                    callback();
                } 
                else if (window.addEventListener) {
                    window.addEventListener("load", callback, false);
                }
                else if (window.attachEvent) {
                    window.attachEvent("onload", callback);
                }
                else
                    window.onload = callback;
            })(window);
        </script>'''

    def __init__(self, attrs=None, format=None, options=None, div_attrs=None, icon_attrs=None):
        if not icon_attrs:
            icon_attrs = {'class': 'glyphicon glyphicon-calendar'}
        if not div_attrs:
            div_attrs = {'class': 'input-group date'}
        if format is None and options and options.get('format'):
            format = self.conv_datetime_format_js2py(options.get('format'))
        super(DateTimePicker, self).__init__(attrs, format)
        if 'class' not in self.attrs:
            self.attrs['class'] = 'form-control'
        self.div_attrs = div_attrs and div_attrs.copy() or {}
        self.icon_attrs = icon_attrs and icon_attrs.copy() or {}
        self.picker_id = self.div_attrs.get('id') or None
        if options == False:  # datetimepicker will not be initalized only when options is False
            self.options = False
        else:
            self.options = options and options.copy() or {}
            lang = get_momentjs_supported_locale()
            if lang:
                self.options['locale'] = lang
            if format and not self.options.get('format') and not self.attrs.get('date-format'):
                self.options['format'] = self.conv_datetime_format_py2js(format)

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''

        try:
            # For django version < 1.11
            input_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        except TypeError:
            # For django version >= 1.11
            extra_attrs = {"type": self.input_type, "name": name}
            if self.attrs:
                extra_attrs.update(self.attrs)
            input_attrs = self.build_attrs(attrs, extra_attrs=extra_attrs)

        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            input_attrs['value'] = force_text(self.format_value(value))
        input_attrs = dict([(key, conditional_escape(val)) for key, val in input_attrs.items()])  # python2.6 compatible
        if not self.picker_id:
             self.picker_id = (input_attrs.get('id', '') +
                               '_pickers').replace(' ', '_')
        self.div_attrs['id'] = self.picker_id
        picker_id = conditional_escape(self.picker_id)
        div_attrs = dict(
            [(key, conditional_escape(val)) for key, val in self.div_attrs.items()])  # python2.6 compatible
        icon_attrs = dict([(key, conditional_escape(val)) for key, val in self.icon_attrs.items()])
        html = self.html_template % dict(div_attrs=flatatt(div_attrs),
                                         input_attrs=flatatt(input_attrs),
                                         icon_attrs=flatatt(icon_attrs))
        if self.options:
            js = self.js_template % dict(picker_id=picker_id,
                                         options=json.dumps(self.options or {}))
        else:
            js = ''
        return mark_safe(force_text(html + js))

    def format_value(self, value):
        """
        The private API ``Widget._format_value()`` is made public and renamed to
        :meth:`~django.forms.Widget.format_value`.The old name will work until
        Django 2.0.
        """
        try:
            return super(DateTimePicker, self).format_value(value)
        except AttributeError:
            return super(DateTimePicker, self)._format_value(value)
