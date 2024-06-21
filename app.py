from flask import Flask, request, render_template, redirect, url_for, flash
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from config import Config
import logging
import os

# Environment setup
from dotenv import load_dotenv
load_dotenv()

# Database setup
client = MongoClient(Config.MONGO_URI, server_api=ServerApi('1'))
try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(e)

app = Flask(__name__)
app.config.from_object(Config)

# Set up logging
if not app.debug:
    logging.basicConfig(filename='error.log', level=logging.ERROR,
                        format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

# Template Manager class
class TemplateManager:
    def __init__(self):
        self.db = mongo_client.email_templates

    def count_templates(self):
        return self.db.templates.count_documents({})

    @staticmethod
    def get_all_templates(page=1, per_page=10):
        """Retrieve templates with pagination."""
        try:
            skip_amount = (page - 1) * per_page
            templates = mongo_client.email_templates.templates.find().skip(skip_amount).limit(per_page)
            return list(templates)
        except Exception as e:
            current_app.logger.error("Failed to retrieve templates: %s", e)
            return []

    @staticmethod
    def get_template_by_id(template_id):
        """Retrieve a specific template by its ID."""
        try:
            return mongo_client.email_templates.templates.find_one({'_id': ObjectId(template_id)})
        except Exception as e:
            current_app.logger.error(f"Error retrieving template by ID {template_id}: {e}")
            return None

    @staticmethod
    def get_templates_by_tag(tag, page=1, per_page=10):
        """Retrieve templates by a specific tag with pagination."""
        try:
            skip_amount = (page - 1) * per_page
            templates = mongo_client.email_templates.templates.find({"tags": tag}).skip(skip_amount).limit(per_page)
            return list(templates)
        except Exception as e:
            current_app.logger.error(f"Error retrieving templates by tag {tag}: {e}")
            return []

    @staticmethod
    def add_template(data):
        """Add a new template to the database."""
        try:
            return mongo_client.email_templates.templates.insert_one(data).inserted_id
        except Exception as e:
            current_app.logger.error(f"Error adding new template: {e}")
            return None

    @staticmethod
    def update_template(template_id, data):
        """Update an existing template."""
        try:
            result = mongo_client.email_templates.templates.update_one({'_id': ObjectId(template_id)}, {'$set': data})
            return result.modified_count > 0  # Indicates a successful update
        except Exception as e:
            current_app.logger.error(f"Error updating template ID {template_id}: {e}")
            return False

    @staticmethod
    def delete_template(template_id):
        """Delete a template by its ID."""
        try:
            result = mongo_client.email_templates.templates.delete_one({'_id': ObjectId(template_id)})
            return result.deleted_count > 0  # Indicates a successful deletion
        except Exception as e:
            current_app.logger.error(f"Error deleting template ID {template_id}: {e}")
            return False

    @staticmethod
    def search_templates(query, page=1, per_page=10):
        """Search templates by text index with pagination."""
        try:
            skip_amount = (page - 1) * per_page
            templates = mongo_client.email_templates.templates.find({"$text": {"$search": query}}).skip(skip_amount).limit(per_page)
            return list(templates)
        except Exception as e:
            current_app.logger.error(f"Error searching templates: {e}")
            return []

    @staticmethod
    def calculate_total_pages(total_items, per_page):
        """Calculate the total number of pages needed to display all items."""
        return (total_items + per_page - 1) // per_page
        
# Flask Routes

@main.route('/')
@main.route('/page/<int:page>')
def index(page=1, per_page=10):
    total_items = current_app.mongo.email_templates.templates.count_documents({})
    total_pages = TemplateManager.calculate_total_pages(total_items, per_page)
    templates = TemplateManager.get_all_templates(page, per_page)
    return render_template('index.html', templates=templates, page=page, total_pages=total_pages)

@main.route('/template/add', methods=['GET', 'POST'])
def add_template():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        tags = request.form.getlist('tags')
        if TemplateManager.add_template({'title': title, 'content': content, 'tags': tags}):
            flash('Template added successfully!')
        else:
            flash('Failed to add template.')
        return redirect(url_for('main.index'))
    return render_template('add_template.html')

@main.route('/template/edit/<template_id>', methods=['GET', 'POST'])
def edit_template(template_id):
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        tags = request.form.getlist('tags')
        if TemplateManager.update_template(template_id, {'title': title, 'content': content, 'tags': tags}):
            flash('Template updated successfully!')
        else:
            flash('Failed to update template.')
        return redirect(url_for('main.index'))
    else:
        template = TemplateManager.get_template_by_id(template_id)
        if template:
            return render_template('edit_template.html', template=template)
        else:
            flash('Template not found.')
            return redirect(url_for('main.index'))

@main.route('/template/delete/<template_id>')
def delete_template(template_id):
    if TemplateManager.delete_template(template_id):
        flash('Template deleted successfully!')
    else:
        flash('Failed to delete template.')
    return redirect(url_for('main.index'))

@main.route('/search', methods=['GET'])
def search_templates():
    query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    total_items = current_app.mongo.email_templates.templates.count_documents({"$text": {"$search": query}})
    total_pages = TemplateManager.calculate_total_pages(total_items, per_page)
    templates = TemplateManager.search_templates(query, page, per_page)
    return render_template('index.html', templates=templates, page=page, total_pages=total_pages)

@main.route('/tags/<tag>/page/<int:page>')
def filter_by_tag(tag, page=1, per_page=10):
    total_items = current_app.mongo.email_templates.templates.count_documents({"tags": tag})
    total_pages = TemplateManager.calculate_total_pages(total_items, per_page)
    templates = TemplateManager.get_templates_by_tag(tag, page, per_page)
    return render_template('index.html', templates=templates, page=page, total_pages=total_pages, tag=tag)
    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
