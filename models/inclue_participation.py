from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class InclueParticipation(models.Model):
    _name = 'inclue.participation'
    _description = 'Tracks user participation in the iN-Clue journey'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Participant',
        required=True,
        help="The partner associated with this participation."
    )
    event_id = fields.Many2one(
        comodel_name='event.event',
        string='Event',
        required=True,
        help="The event associated with this participation."
    )
    survey_id = fields.Many2one(
        comodel_name='survey.survey',
        string='Linked Survey',
        help="The survey associated with this participation."
    )
    user_input_id = fields.Many2one(
        comodel_name='survey.user_input',
        string='Survey Response',
        help="The user's response to the survey."
    )
    survey_sent = fields.Boolean(
        string='Survey Sent',
        default=False,
        help="Indicates if the survey has been sent to the participant."
    )
    session_type = fields.Selection([
        ('kickoff', 'KickOff Session'),
        ('followup1', 'FollowUp Session 1'),
        ('followup2', 'FollowUp Session 2'),
        ('followup3', 'FollowUp Session 3'),
        ('followup4', 'FollowUp Session 4'),
        ('followup5', 'FollowUp Session 5'),
        ('followup6', 'FollowUp Session 6'),
    ], string='Session Type', default='kickoff')
    completed = fields.Boolean(
        string='Completed',
        default=False,
        help="Indicates if the participation has been completed."
    )
    date_completed = fields.Datetime(
        string='Completion Date',
        help="The date when the participation was completed."
    )

    @api.model
    def create(self, vals):
        _logger.info("Creating a new inclue.participation record with vals: %s", vals)
        participation = super(InclueParticipation, self).create(vals)
        _logger.info("Created inclue.participation record with ID: %s", participation.id)
        if participation.survey_id and not participation.survey_sent:
            _logger.info("Survey is linked and not sent yet. Attempting to send email for participation ID: %s", participation.id)
            participation.send_survey_email()
        return participation
    
    # def send_survey_email(self):
    #     _logger.info("send_survey_emails() called for participation ID: %s", self.id)
    #      # Log the user email that would be used in the template
    #     _logger.info(f"Current user email for template: {self.env.user.email or 'No email found'}")
    
    #     # Get the template
    #     template = self.env.ref('in_clue_event_surveys.mail_template_inclue_survey', raise_if_not_found=False)
    #     if not template:
    #         _logger.error("❌ Survey email template not found for participation ID: %s. Skipping survey sending.", self.id)
    #         return False

    #     try:
    #         # Create the mail (but don't send yet)
    #         mail_id = template.send_mail(self.id, force_send=False)  # force_send=False = queued
    #         mail = self.env['mail.mail'].browse(mail_id)
            
    #         _logger.info(
    #             "📨 Mail %s created from template ID %s for %s. State=%s, From=%s, To=%s",
    #             mail_id, template.id, self.partner_id.email, mail.state, mail.email_from, mail.email_to
    #         )

    #         # Send it manually and catch any SMTP-level issues
    #         mail.send(raise_exception=True)

    #         # Mark as sent
    #         self.survey_sent = True
    #         _logger.info("✅ Survey email successfully sent via SMTP to %s (Mail ID: %s)", self.partner_id.email, mail_id)
    #         return True

    #     except Exception as e:
    #         _logger.exception("❌ Failed to send iN-Clue survey email to %s for participation ID: %s. Exception: %s", self.partner_id.email, self.id, e)
    #         return False

    def send_survey_email(self):
        _logger.info("send_survey_email() called for participation ID: %s", self.id)

        # Get the template
        template = self.env.ref('in_clue_event_surveys.mail_template_inclue_survey', raise_if_not_found=False)
        if not template:
            _logger.error("❌ Survey email template not found for participation ID: %s. Skipping survey sending.", self.id)
            return False

        try:
            # Generate the user input if not yet generated
            if not self.user_input_id:
                user_input = self.env['survey.user_input'].create({
                    'survey_id': self.survey_id.id,
                    'partner_id': self.partner_id.id,
                })
                _logger.info("Survey user_input created with ID %s", user_input.id)
            else:
                user_input = self.user_input_id
            
            # Check if the user_input has a token
            if not user_input.access.token:
                _logger.error("❌ No token found for user_input ID: %s. Skipping survey email sending.", user_input.id)
                return False

            # Construct the survey link
            survey_link = user_input.survey_id.get_start_url(user_input.access.token)

            # Send email using the template
            mail_id = template.send_mail(self.id, force_send=False)  # force_send=False = queued
            mail = self.env['mail.mail'].browse(mail_id)

            _logger.info(
                "📨 Mail %s created from template ID %s for %s. State=%s, From=%s, To=%s",
                mail_id, template.id, self.partner_id.email, mail.state, mail.email_from, mail.email_to
            )

            # Send it manually and catch any SMTP-level issues
            mail.send(raise_exception=True)

            # Mark as sent
            self.survey_sent = True
            _logger.info("✅ Survey email successfully sent to %s (Mail ID: %s)", self.partner_id.email, mail_id)
            return True

        except Exception as e:
            _logger.exception("❌ Failed to send survey email to %s for participation ID: %s. Exception: %s", self.partner_id.email, self.id, e)
            return False


    # def send_survey_email(self):
    #     _logger.info("send_survey_email() called for participation ID: %s", self.id)
    #     template = self.env.ref('in_clue_event_surveys.mail_template_inclue_survey', raise_if_not_found=False)
    #     if not template:
    #         _logger.error("❌ Survey email template not found for participation ID: %s. Skipping survey sending.", self.id)
    #         return False

    #     try:
    #         _logger.info("Using email template (ID: %s) to send mail to %s", template.id, self.partner_id.email)
    #         template.send_mail(self.id, force_send=True)
    #         self.survey_sent = True
    #         _logger.info("✅ Successfully sent iN-Clue survey email to %s for participation ID: %s", self.partner_id.email, self.id)
    #         return True
    #     except Exception as e:
    #         _logger.exception("❌ Failed to send iN-Clue survey email to %s for participation ID: %s. Exception: %s", self.partner_id.email, self.id, e)
    #         return False

    # def send_survey_email(self):
    #     template = self.env.ref('in_clue_event_surveys.mail_template_inclue_survey', raise_if_not_found=False)
    #     if not template:
    #         _logger.error("Template not found.")
    #         return False

    #     # Generate the mail values
    #     mail_id = template.send_mail(self.id, force_send=True)
    #     mail = self.env['mail.mail'].browse(mail_id)
    #     _logger.info("Mail %s created: state=%s, from=%s, to=%s", 
    #         mail_id, mail.state, mail.email_from, mail.email_to
    #     )
    #     # Force immediate send (raises if SMTP fails)
    #     try:
    #         mail.send(raise_exception=True)
    #         _logger.info("Mail %s successfully sent via SMTP", mail_id)
    #         self.survey_sent = True
    #         return True
    #     except Exception as e:
    #         _logger.exception("Failed to send mail %s: %s", mail_id, e)
    #         return False
