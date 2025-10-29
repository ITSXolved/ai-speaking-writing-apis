# app/services/email_service.py
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import Optional, List, Dict, Any
from jinja2 import Template
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_address = os.getenv("SENDER_EMAIL")
        self.email_password = os.getenv("SENDER_EMAIL_PASSWORD")
        self.use_tls = os.getenv("USE_TLS", "true").lower() == "true"
        
        if not self.email_address or not self.email_password:
            raise ValueError("Email credentials not configured properly")

    async def send_learning_report(
        self,
        recipient_email: str,
        user_name: str,
        report_data: Dict[str, Any],
        report_type: str = "weekly"
    ) -> bool:
        """
        Send learning progress report to user
        """
        try:
            subject = f"Your {report_type.title()} Language Learning Report"
            
            # Generate HTML content from template
            html_content = self._generate_report_html(user_name, report_data, report_type)
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_address
            message["To"] = recipient_email
            
            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email
            return await self._send_email(message, recipient_email)
            
        except Exception as e:
            logger.error(f"Failed to send learning report: {str(e)}")
            return False

    async def send_writing_feedback_report(
        self,
        recipient_email: str,
        user_name: str,
        original_text: str,
        feedback: Dict[str, Any],
        improved_version: str
    ) -> bool:
        """
        Send writing evaluation feedback report
        """
        try:
            subject = "Your Writing Evaluation & Improvement Report"
            
            html_content = self._generate_writing_feedback_html(
                user_name, original_text, feedback, improved_version
            )
            
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_address
            message["To"] = recipient_email
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            return await self._send_email(message, recipient_email)
            
        except Exception as e:
            logger.error(f"Failed to send writing feedback report: {str(e)}")
            return False

    async def _send_email(self, message: MIMEMultipart, recipient: str) -> bool:
        """
        Internal method to send email via SMTP
        """
        try:
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                server.login(self.email_address, self.email_password)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"SMTP error: {str(e)}")
            return False

    def _generate_report_html(self, user_name: str, report_data: Dict[str, Any], report_type: str) -> str:
        """
        Generate HTML content for learning progress report
        """
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Language Learning Report</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px; }
                .content { background: #f9f9f9; padding: 30px; margin: 20px 0; border-radius: 10px; }
                .metric { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #667eea; }
                .improvement { color: #27ae60; font-weight: bold; }
                .footer { text-align: center; margin-top: 30px; color: #666; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎓 Your {{ report_type.title() }} Language Learning Report</h1>
                <p>Hello {{ user_name }}! Here's your progress summary.</p>
            </div>
            
            <div class="content">
                <h2>📊 Learning Statistics</h2>
                
                <div class="metric">
                    <h3>⏱️ Study Time</h3>
                    <p><strong>{{ report_data.total_study_time }} minutes</strong> this {{ report_type }}</p>
                    <p class="improvement">+{{ report_data.time_improvement }}% from last {{ report_type }}</p>
                </div>
                
                <div class="metric">
                    <h3>💬 Conversations</h3>
                    <p><strong>{{ report_data.total_conversations }}</strong> practice sessions completed</p>
                    <p>Average session length: <strong>{{ report_data.avg_session_length }} minutes</strong></p>
                </div>
                
                <div class="metric">
                    <h3>🎯 Language Skills</h3>
                    <ul>
                        {% for skill, score in report_data.skill_scores.items() %}
                        <li><strong>{{ skill.title() }}:</strong> {{ score }}/100</li>
                        {% endfor %}
                    </ul>
                </div>
                
                <div class="metric">
                    <h3>🏆 Achievements</h3>
                    <ul>
                        {% for achievement in report_data.achievements %}
                        <li>{{ achievement }}</li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
            
            <div class="footer">
                <p>Keep up the great work! 🌟</p>
                <p><em>Generated on {{ current_date }}</em></p>
            </div>
        </body>
        </html>
        """
        
        template = Template(template_str)
        return template.render(
            user_name=user_name,
            report_data=report_data,
            report_type=report_type,
            current_date=datetime.now().strftime("%Y-%m-%d %H:%M")
        )

    def _generate_writing_feedback_html(
        self, 
        user_name: str, 
        original_text: str, 
        feedback: Dict[str, Any], 
        improved_version: str
    ) -> str:
        """
        Generate HTML content for writing feedback report
        """
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Writing Evaluation Report</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; text-align: center; border-radius: 10px; }
                .section { background: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 10px; }
                .original { border-left: 4px solid #e74c3c; }
                .improved { border-left: 4px solid #27ae60; }
                .feedback { border-left: 4px solid #3498db; }
                .score { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; display: inline-block; }
                .highlight { background: #fff3cd; padding: 2px 4px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✍️ Writing Evaluation Report</h1>
                <p>Hello {{ user_name }}! Here's your detailed writing feedback.</p>
            </div>
            
            <div class="section">
                <h2>📊 Overall Scores</h2>
                {% for category, score in feedback.scores.items() %}
                <div class="score">
                    <strong>{{ category.replace('_', ' ').title() }}:</strong> {{ score }}/100
                </div>
                {% endfor %}
            </div>
            
            <div class="section original">
                <h2>📝 Your Original Text</h2>
                <p style="background: white; padding: 15px; border-radius: 5px;">{{ original_text }}</p>
            </div>
            
            <div class="section feedback">
                <h2>🔍 Detailed Feedback</h2>
                
                <h3>✅ Strengths</h3>
                <ul>
                    {% for strength in feedback.strengths %}
                    <li>{{ strength }}</li>
                    {% endfor %}
                </ul>
                
                <h3>⚠️ Areas for Improvement</h3>
                <ul>
                    {% for improvement in feedback.improvements %}
                    <li>{{ improvement }}</li>
                    {% endfor %}
                </ul>
                
                <h3>📚 Grammar & Style Suggestions</h3>
                <ul>
                    {% for suggestion in feedback.suggestions %}
                    <li>{{ suggestion }}</li>
                    {% endfor %}
                </ul>
            </div>
            
            <div class="section improved">
                <h2>✨ Improved Version</h2>
                <p style="background: white; padding: 15px; border-radius: 5px;">{{ improved_version }}</p>
            </div>
            
            <div style="text-align: center; margin-top: 30px; color: #666;">
                <p>Keep practicing your writing skills! 📖✨</p>
                <p><em>Generated on {{ current_date }}</em></p>
            </div>
        </body>
        </html>
        """
        
        template = Template(template_str)
        return template.render(
            user_name=user_name,
            original_text=original_text,
            feedback=feedback,
            improved_version=improved_version,
            current_date=datetime.now().strftime("%Y-%m-%d %H:%M")
        )