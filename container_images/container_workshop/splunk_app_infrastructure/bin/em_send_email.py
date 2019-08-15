# coding=utf-8

import logging_utility
import datetime
import re
import urllib
import em_common
import em_constants as EMConstants
import em_declare  # noqa
import splunk.entity as entity
import splunk.secure_smtplib as secure_smtplib
import splunk.ssl_context as ssl_context
from smtplib import SMTPAuthenticationError, SMTPException, SMTPHeloError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from collections import namedtuple
from em_abstract_custom_alert_action import AbstractCustomAlertAction
from service_manager.splunkd.kvstore import KVStoreManager
from splunk.util import normalizeBoolean

logger = logging_utility.getLogger()

CHARSET = 'UTF-8'
EMAIL_DELIM = re.compile('\s*[,;]\s*')
ALERT_SEVERITY = {
    '1': 'INFO',
    '3': 'WARNING',
    '5': 'CRITICAL'
}

EMAIL_BODY_HTML = """\
    <html>
    <head></head>
    <body>
        <div>
            <span>Alert Title :</span>
            <b>{alert_title}</b>
        </div>
        <div>
            <span>Severity :</span>
                <b>{alert_severity} {metric_name} : {current_value}</b>
        </div>
        {aggregation_section}
        <div>
            <span>{manage_by_type} triggered this alert:</span>
            <b>{manage_by_value}</b>
        </div>
        <div>
            <span>{manage_by_type} id:</span>
            <b>{manage_by_id}</b>
        </div>
        {group_definition_section}
        {split_by_section}
        {metric_filters_section}
        <div>
            <span>Time triggered:</span>
            <b>{triggered_time}</b>
        </div>
        <div><a href="{maw_url}">Investigate Now</a></div>
    </body>
    </html>
    """

SPLIT_BY_HTML = """\
    <div>
        <span>Split-by:</span>
        <b>{split_by}={split_by_value}</b>
    </div>
    """

AGGREGATION_HTML = """\
    <div>
        <span>Aggregation:</span>
        <b>{aggregation_method}</b>
    </div>
    """

GROUP_DEFINITION_HTML = """\
    <div>
        <span>Group definition:</span>
        <b>{group_filter}</b>
    </div>
    """

METRIC_FILTERS_HTML = """\
    <div>
        <span>Metric filters ({section_type}):</span>
        {metric_filters}
    </div>
    """

EmailContent = namedtuple('EmailContent', 'sender recipients email')


class EMSendEmailAlertAction(AbstractCustomAlertAction):
    """
    Reads the results from the saved search and sends a custom email based on the configuration.
    """
    ssContent = None
    sessionKey = None

    def getAlertActions(self, namespace=None):
        """
        Fetches the email alert settings
        """
        settings = None
        try:
            settings = entity.getEntity(
                '/configs/conf-alert_actions',
                'email',
                sessionKey=self.sessionKey, owner='nobody', namespace=namespace)
        except Exception as e:
            logger.error('Could not access or parse email stanza of alert_actions.conf. Error=%s' % str(e))
        return settings

    def make_email_subject(self, result, payload):
        """
        Subject for the email template
        """
        return '[Splunk] %s : %s ' % (ALERT_SEVERITY[result.get('current_state')], payload.get('search_name'))

    def make_email_body(self, result, payload):
        """
        Constructs the body of the email template . The body is a html string which is formated with
        the values from the results
        """
        def metric_filters_section_helper(metric_filters_str):
            rv = ''
            if metric_filters_str:
                for metric_filter_str in metric_filters_str.split('; '):
                    rv += """
                        <br />
                        <span style="padding-left:2em;"><b>%s</b></span>
                        """ % metric_filter_str
            return rv

        settings = payload.get('configuration')
        session_key = payload.get('session_key')
        trigger_time = None
        if settings:
            trigger_time = datetime.datetime.utcfromtimestamp(
                float(settings.get('trigger_time'))).strftime('%Y-%m-%dT%H:%M:%SZ')

        managed_by_id = result.get('managed_by_id')
        managed_by_type = result.get('managed_by_type')
        entity_title = result.get('entity_title', '')
        aggregation_method = result.get('aggregation_method', '').lower()
        # Metrics filter section
        metric_filters_incl = result.get('metric_filters_incl', '')
        metric_filters_excl = result.get('metric_filters_excl', '')
        metric_filters_section = ''
        if (metric_filters_incl):
            metric_filters_section += METRIC_FILTERS_HTML.format(
                section_type='inclusive',
                metric_filters=metric_filters_section_helper(metric_filters_incl),
            )
        if (metric_filters_excl):
            metric_filters_section += METRIC_FILTERS_HTML.format(
                section_type='exclusive',
                metric_filters=metric_filters_section_helper(metric_filters_excl),
            )
        # Split-by identifier dimensions gives no split_by_value but adds entity_title
        split_by = result.get('split_by', '')
        split_by_value = result.get(split_by, entity_title)
        aggregation_section = AGGREGATION_HTML.format(
            aggregation_method=aggregation_method)

        # Split-by alert
        if (split_by != 'None'):
            split_by_section = SPLIT_BY_HTML.format(split_by=split_by,
                                                    split_by_value=split_by_value)
        else:
            split_by_section = ''

        if managed_by_type == 'entity':
            managed_by_value = entity_title
            group_definition_section = ''
        else:
            # Fetch group information
            kvstore = KVStoreManager(collection=EMConstants.STORE_GROUPS,
                                     server_uri=em_common.get_server_uri(),
                                     session_key=session_key,
                                     app=EMConstants.APP_NAME)
            kvstore_output = kvstore.get(managed_by_id)
            group_filter = kvstore_output.get('filter', '').replace(',', ', ')
            managed_by_value = kvstore_output.get('title', '')

            group_definition_section = GROUP_DEFINITION_HTML.format(
                group_filter=group_filter)

        alert_title = payload.get('search_name')
        # set URL that points to MAW with corresponding alert panel open
        url = self._make_alert_url(managed_by_type, managed_by_id, alert_title)

        body = EMAIL_BODY_HTML.format(alert_title=alert_title,
                                      alert_severity=ALERT_SEVERITY[result.get('current_state')],
                                      metric_name=result.get('metric_name'),
                                      current_value=round(float(result.get('current_value', 0)), 2),
                                      manage_by_type=managed_by_type,
                                      manage_by_value=managed_by_value,
                                      manage_by_id=managed_by_id,
                                      group_definition_section=group_definition_section,
                                      aggregation_section=aggregation_section,
                                      split_by_section=split_by_section,
                                      triggered_time=trigger_time,
                                      metric_filters_section=metric_filters_section,
                                      maw_url=url,
                                      )
        return body

    def _make_alert_url(self, managed_by_type, managed_by_id, alert_name):
        url_params = [
            (managed_by_type, managed_by_id),
            ('alert_name', alert_name),
            ('tab', 'ANALYSIS')
        ]
        url_template = '{base_url}/app/splunk_app_infrastructure/metrics_analysis?{encoded_params}'
        splunkweb_url = em_common.get_splunkweb_fqdn()
        url = url_template.format(
            base_url=splunkweb_url if not em_common.is_splunk_cloud(splunkweb_url) else splunkweb_url.rsplit(":", 1)[0],
            encoded_params=urllib.urlencode(url_params)
        )
        return url

    def construct_email(self, result, sender, recipients, payload):
        """
        Constructs the email object with the right MIME type
        """
        email = MIMEMultipart()
        body = self.make_email_body(result, payload)
        email_body = MIMEText(body, 'html')
        email.attach(email_body)
        email['From'] = sender
        email['To'] = ', '.join(recipients)
        email['Subject'] = Header(self.make_email_subject(result, payload), CHARSET)
        return email.as_string()

    def get_email_content(self, result, payload):
        """
        - Returns a Tuple with all info to send email
        """
        sender = self.ssContent.get('from', 'no-reply@splunk.com')
        settings = payload.get('configuration')
        recipients = [r.strip() for r in settings.get('email_to', '').split(',')]
        email = self.construct_email(result, sender, recipients, payload)
        mail_log_msg = 'Sending email="%s", recipients="%s"' % (
            email,
            recipients
        )
        try:
            return EmailContent(sender=sender, recipients=recipients, email=email)
        except Exception, e:
            logger.error(str(e))
            logger.info(mail_log_msg)

    def _setup_smtp(self, payload):
        """
        Setup smtp to send out a group of emails.
        """
        use_ssl = normalizeBoolean(self.ssContent.get('use_ssl', False))
        use_tls = normalizeBoolean(self.ssContent.get('use_tls', False))
        server = self.ssContent.get('mailserver', 'localhost')
        username = self.ssContent.get('auth_username', '')
        password = self.ssContent.get('clear_password', '')

        # setup the Open SSL Context
        sslHelper = ssl_context.SSLHelper()
        serverConfJSON = sslHelper.getServerSettings(self.sessionKey)
        # Pass in settings from alert_actions.conf into context
        ctx = sslHelper.createSSLContextFromSettings(
            sslConfJSON=self.ssContent,
            serverConfJSON=serverConfJSON,
            isClientContext=True)

        # send the mail
        if not use_ssl:
            smtp = secure_smtplib.SecureSMTP(host=server)
        else:
            smtp = secure_smtplib.SecureSMTP_SSL(host=server, sslContext=ctx)
        # smtp.set_debuglevel(1)
        if use_tls:
            smtp.starttls(ctx)

        if username and password and username.strip() and password.strip():
            try:
                smtp.login(username, password)
            except SMTPAuthenticationError as e:
                logger.error('Email server: fail to authenticate: %s' % e)
            except SMTPHeloError as e:
                logger.error('Email server: fail to reply to hello: %s' % e)
            except SMTPException as e:
                logger.error('Email server: fail to find suitable authentication method: %s' % e)
        else:
            logger.warning('Email server: using unauthenticated connection to SMTP server')

        return smtp

    def execute(self, results, payload):
        """
        Loop through the results and send email based on settings.
        """
        if not results:
            return

        namespace = payload.get('namespace', 'splunk_app_infrastructure')
        self.sessionKey = payload.get('session_key')
        self.ssContent = self.ssContent if self.ssContent else self.getAlertActions(namespace)

        settings = payload.get('configuration')
        email_states = [r.strip() for r in settings.get('email_when', '').split(',')]
        mails_to_send = []
        for row in results:
            state_change = row.get('state_change', 'no')
            if state_change != 'no' and state_change in email_states \
                    and row.get('current_state') is not 'None':
                mails_to_send.append(self.get_email_content(row, payload))

        # check if mails need to be send, create smtp and send
        if len(mails_to_send) > 0:
            smtp = self._setup_smtp(payload)
            for item in mails_to_send:
                # in case default recipients are added
                recipients = item.recipients
                if self.ssContent.get('to'):
                    recipients.extend(EMAIL_DELIM.split(self.ssContent.get('to')))
                smtp.sendmail(item.sender, recipients, item.email)
            smtp.quit()

        return results


instance = EMSendEmailAlertAction()

if __name__ == '__main__':
    instance.run()
