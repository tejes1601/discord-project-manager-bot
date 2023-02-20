# -*- coding: utf-8 -*-
"""
Created on Mon Feb 20 08:03:34 2023

@author: tejes
"""

import os
import discord
from discord.ext import commands
import sqlite3
import requests
import smtplib
from email.mime.text import MIMEText
import asyncio

# Set up database
conn = sqlite3.connect('tickets.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS tickets
             (ticket_id INTEGER PRIMARY KEY, creator_id INTEGER, description TEXT, status TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS tasks
             (task_id INTEGER PRIMARY KEY, assignee_id INTEGER, task_name TEXT, status TEXT, create_time TIMESTAMP)''')
conn.commit()

# Set up email sender
def send_email(recipient, message):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    email_sender = 'your_email@gmail.com'
    email_password = 'your_email_password'

    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(email_sender, email_password)
        msg = MIMEText(message)
        msg['Subject'] = 'Task Reminder'
        msg['From'] = email_sender
        msg['To'] = recipient
        smtp.send_message(msg)

# Set up WhatsApp sender
def send_whatsapp(number, message):
    whatsapp_url = f'https://api.whatsapp.com/send?phone={number}&text={message}'
    requests.get(whatsapp_url)

# Set up bot
bot = commands.Bot(command_prefix='/')

@bot.command(name='ticket')
async def raise_ticket(ctx, description):
    # Add ticket to database
    c.execute("INSERT INTO tickets (creator_id, description, status) VALUES (?, ?, 'Open')", (ctx.author.id, description))
    conn.commit()
    await ctx.send('Ticket raised successfully!')

@bot.command(name='tickets')
async def view_tickets(ctx):
    # Get all open tickets from database
    c.execute("SELECT * FROM tickets WHERE status='Open'")
    tickets = c.fetchall()

    # Display open tickets in a table
    table = f"{'ID':<5}{'Creator':<20}{'Description':<50}{'Status':<10}\n"
    for ticket in tickets:
        creator = bot.get_user(ticket[1])
        table += f"{ticket[0]:<5}{creator.name:<20}{ticket[2]:<50}{ticket[3]:<10}\n"
    await ctx.send(f"```{table}```")

@bot.command(name='assign')
async def assign_task(ctx, ticket_id: int, assignee: discord.Member, description):
    # Add task to database
    c.execute("INSERT INTO tasks (assignee_id, task_name, status, create_time) VALUES (?, ?, 'Open', ?)", (assignee.id, description, discord.utils.utcnow()))
    conn.commit()
    await ctx.send(f'Task assigned to {assignee.name}!')
                   
    # Update the status of the ticket in the database
    c.execute("UPDATE tickets SET status='Closed' WHERE ticket_id=?", (ticket_id,))
    conn.commit()

    # Notify the ticket creator that their ticket has been closed
    c.execute("SELECT creator_id, description FROM tickets WHERE ticket_id=?", (ticket_id,))
    result = c.fetchone()
    creator = bot.get_user(result[0])
    description = result[1]
    message = f"Your ticket '{description}' has been closed."
    send_email(creator.email, message)
    await ctx.send(f"Ticket '{description}' has been closed.")


@bot.command(name='close_task')
async def close_task(ctx, task_id):
    # Update the status of the task in the database
    c.execute("UPDATE tasks SET status='Closed' WHERE task_id=?", (task_id,))
    conn.commit()

    # Notify the task assignee that their task has been closed
    c.execute("SELECT assignee_id, task_name FROM tasks WHERE task_id=?", (task_id,))
    result = c.fetchone()
    assignee = bot.get_user(result[0])
    task_name = result[1]
    message = f"Your task '{task_name}' has been closed."
    send_whatsapp(assignee.phone, message)
    await ctx.send(f"Task '{task_name}' has been closed.")

@bot.command(name='remind')
async def remind_assignee(ctx, task_id):
    # Get the task assignee from the database
    c.execute("SELECT assignee_id, task_name FROM tasks WHERE task_id=?", (task_id,))
    result = c.fetchone()
    assignee = bot.get_user(result[0])
    task_name = result[1]

    # Send a reminder message to the task assignee
    message = f"Reminder: You have an open task '{task_name}'. Please complete it as soon as possible."
    send_email(assignee.email, message)
    await ctx.send(f"Reminder sent to {assignee.name}.")

bot.run(os.environ['MTA3NzA1MDA2NDY5NTk4ODIyNA.GkgBbg.m6Rp_T9RfsMt2qB-aHyuWSQTtNfaGD64IQFI6M'])
