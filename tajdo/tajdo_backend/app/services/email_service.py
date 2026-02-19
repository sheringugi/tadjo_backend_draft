import resend
import os
from datetime import datetime

class EmailService:
    
    def __init__(self):
        resend.api_key = os.getenv('RESEND_API_KEY')
        self.from_email = os.getenv('FROM_EMAIL', 'onboarding@resend.dev')
        self.from_name = os.getenv('FROM_NAME', 'TAJDO')
            
    def send_email(self, to_email: str, subject: str, html_content: str):
        """Send an email via Resend"""
        try:
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
            email = resend.Emails.send(params)
            print(f"Email sent to {to_email}: ID {email.get('id')}")
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    def send_order_confirmation(self, order, user):
        """Send order confirmation email"""
        subject = f"Order Confirmation - {order.order_number}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #F5F0EB; padding: 30px; text-align: center; }}
                .header h1 {{ color: #2C2C2C; margin: 0; font-size: 28px; }}
                .content {{ padding: 30px 20px; }}
                .order-info {{ background-color: #F5F0EB; padding: 20px; margin: 20px 0; }}
                .order-info p {{ margin: 8px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .button {{ 
                    display: inline-block; 
                    background-color: #2C2C2C; 
                    color: white; 
                    padding: 12px 30px; 
                    text-decoration: none; 
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>TAJDO</h1>
                    <p style="margin: 10px 0 0 0; color: #666;">Thank you for your order</p>
                </div>
                
                <div class="content">
                    <p>Dear {user.full_name or 'Valued Customer'},</p>
                    
                    <p>We've received your order and we're getting it ready. You'll receive another email when your order has been shipped.</p>
                    
                    <div class="order-info">
                        <p><strong>Order Number:</strong> {order.order_number}</p>
                        <p><strong>Order Date:</strong> {order.created_at.strftime('%B %d, %Y')}</p>
                        <p><strong>Total:</strong> CHF {order.total:.2f}</p>
                        <p><strong>Payment Method:</strong> {order.payment_method.title()}</p>
                    </div>
                    
                    <p style="text-align: center;">
                        <a href="http://localhost:5173/track-order?order_number={order.order_number}&email={user.email}" class="button">
                            Track Your Order
                        </a>
                    </p>
                    
                    <p>If you have any questions, please don't hesitate to contact us.</p>
                    
                    <p>With every purchase, 30% goes to TAJDO Rescue to help dogs in need.</p>
                    
                    <p style="margin-top: 30px;">Best regards,<br>The TAJDO Team</p>
                </div>
                
                <div class="footer">
                    <p>TAJDO - Luxury with Purpose</p>
                    <p>This email was sent to {user.email}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user.email, subject, html_content)
    
    def send_order_shipped(self, order, user, tracking_number: str = None):
        """Send order shipped email"""
        subject = f"Your Order Has Shipped - {order.order_number}"
        
        tracking_info = ""
        if tracking_number:
            tracking_info = f"<p><strong>Tracking Number:</strong> {tracking_number}</p>"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #F5F0EB; padding: 30px; text-align: center; }}
                .header h1 {{ color: #2C2C2C; margin: 0; font-size: 28px; }}
                .content {{ padding: 30px 20px; }}
                .order-info {{ background-color: #F5F0EB; padding: 20px; margin: 20px 0; }}
                .order-info p {{ margin: 8px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📦 Your Order is On Its Way!</h1>
                </div>
                
                <div class="content">
                    <p>Dear {user.full_name or 'Valued Customer'},</p>
                    
                    <p>Great news! Your TAJDO order has been shipped and is on its way to you.</p>
                    
                    <div class="order-info">
                        <p><strong>Order Number:</strong> {order.order_number}</p>
                        {tracking_info}
                        <p><strong>Estimated Delivery:</strong> 3-7 business days</p>
                    </div>
                    
                    <p>You can track your order status at any time on our website.</p>
                    
                    <p style="margin-top: 30px;">Best regards,<br>The TAJDO Team</p>
                </div>
                
                <div class="footer">
                    <p>TAJDO - Luxury with Purpose</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user.email, subject, html_content)
    
    def send_order_delivered(self, order, user):
        """Send order delivered email"""
        subject = f"Your Order Has Been Delivered - {order.order_number}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #F5F0EB; padding: 30px; text-align: center; }}
                .header h1 {{ color: #2C2C2C; margin: 0; font-size: 28px; }}
                .content {{ padding: 30px 20px; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ Delivery Confirmed</h1>
                </div>
                
                <div class="content">
                    <p>Dear {user.full_name or 'Valued Customer'},</p>
                    
                    <p>Your TAJDO order ({order.order_number}) has been successfully delivered!</p>
                    
                    <p>We hope you and your furry friend love your new products. Remember, 30% of your purchase supports TAJDO Rescue.</p>
                    
                    <p>If you have any questions or concerns about your order, please don't hesitate to contact us.</p>
                    
                    <p style="margin-top: 30px;">Best regards,<br>The TAJDO Team</p>
                </div>
                
                <div class="footer">
                    <p>TAJDO - Luxury with Purpose</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user.email, subject, html_content)
    
    def send_order_cancelled(self, order, user):
        """Send order cancelled email"""
        subject = f"Order Cancelled - {order.order_number}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #F5F0EB; padding: 30px; text-align: center; }}
                .header h1 {{ color: #2C2C2C; margin: 0; font-size: 28px; }}
                .content {{ padding: 30px 20px; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Order Cancelled</h1>
                </div>
                
                <div class="content">
                    <p>Dear {user.full_name or 'Valued Customer'},</p>
                    
                    <p>Your TAJDO order ({order.order_number}) has been cancelled.</p>
                    
                    <p>If you have already paid for this order, a refund will be processed shortly.</p>
                    
                    <p>If you have any questions or believe this was a mistake, please contact our support team.</p>
                    
                    <p style="margin-top: 30px;">Best regards,<br>The TAJDO Team</p>
                </div>
                
                <div class="footer">
                    <p>TAJDO - Luxury with Purpose</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user.email, subject, html_content)

    def send_order_refunded(self, order, user):
        """Send order refunded email"""
        subject = f"Refund Processed - {order.order_number}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; color: #333; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #F5F0EB; padding: 30px; text-align: center; }}
                .header h1 {{ color: #2C2C2C; margin: 0; font-size: 28px; }}
                .content {{ padding: 30px 20px; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Refund Processed</h1>
                </div>
                
                <div class="content">
                    <p>Dear {user.full_name or 'Valued Customer'},</p>
                    
                    <p>A refund has been processed for your TAJDO order ({order.order_number}).</p>
                    
                    <p>The amount of CHF {order.total:.2f} should appear in your account within 5-10 business days, depending on your bank.</p>
                    
                    <p>If you have any questions, please don't hesitate to contact us.</p>
                    
                    <p style="margin-top: 30px;">Best regards,<br>The TAJDO Team</p>
                </div>
                
                <div class="footer">
                    <p>TAJDO - Luxury with Purpose</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user.email, subject, html_content)