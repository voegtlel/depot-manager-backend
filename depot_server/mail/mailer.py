import aiosmtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mako.lookup import TemplateLookup
from typing import Tuple

from depot_server.config import config


class Mailer:
    def __init__(self):
        self.template_lookup = TemplateLookup(
            directories=[os.path.join(os.path.dirname(__file__), 'mail_templates')],
            strict_undefined=True,
        )

    def async_mailer(self) -> aiosmtplib.SMTP:
        if config.mail.ssl:
            port = 465
        elif config.mail.starttls:
            port = 587
        else:
            port = 25
        if config.mail.port is not None:
            port = config.mail.port

        return aiosmtplib.SMTP(
            config.mail.host,
            port,
            username=config.mail.user,
            password=config.mail.password,
            use_tls=config.mail.ssl,
            start_tls=config.mail.starttls,
            client_cert=config.mail.certfile,
            client_key=config.mail.keyfile,
        )

    def _render_template(self, language: str, name: str, **kwargs) -> Tuple[str, str]:
        if language != 'en_us' and not self.template_lookup.has_template(f'{language}/{name}'):
            language = 'en_us'

        template = self.template_lookup.get_template(f'{language}/{name}')
        data = template.render(
            config=config,
            **kwargs,
        )
        return data.split('\n', 1)

    async def async_send_mail(self, language: str, name: str, to: str, context: dict):
        html_title, html_data = self._render_template(language, name + '.html', **context)
        txt_title, txt_data = self._render_template(language, name + '.txt', **context)
        assert txt_title == html_title

        message = MIMEMultipart('alternative')
        message['Subject'] = txt_title
        message.attach(MIMEText(html_data, 'html'))
        message.attach(MIMEText(txt_data, 'plain'))

        async with self.async_mailer() as connected_mailer:
            await connected_mailer.sendmail(config.mail.sender, [to], message.as_bytes())


mailer = Mailer()
