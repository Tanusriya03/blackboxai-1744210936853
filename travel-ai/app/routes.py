from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Itinerary, Place
import requests
import json

main_bp = Blueprint('main', __name__)

# Sample travel data for Indian destinations (would normally use an API)
INDIAN_DESTINATIONS = {
    "Delhi": {
        "hotels": [
            {"name": "The Leela Palace", "price_range": "₹15,000-₹25,000", "rating": 4.8},
            {"name": "ITC Maurya", "price_range": "₹12,000-₹20,000", "rating": 4.7}
        ],
        "attractions": [
            {"name": "Red Fort", "category": "Historical", "time_needed": "3-4 hours"},
            {"name": "India Gate", "category": "Landmark", "time_needed": "1-2 hours"}
        ]
    },
    "Goa": {
        "hotels": [
            {"name": "Taj Exotica", "price_range": "₹20,000-₹35,000", "rating": 4.9},
            {"name": "Grand Hyatt", "price_range": "₹15,000-₹25,000", "rating": 4.6}
        ],
        "attractions": [
            {"name": "Palolem Beach", "category": "Beach", "time_needed": "Full day"},
            {"name": "Old Goa Churches", "category": "Historical", "time_needed": "2-3 hours"}
        ]
    }
}

@main_bp.route('/')
@login_required
def index():
    return render_template('index.html')

@main_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        destination = request.form.get('destination')
        days = int(request.form.get('days'))
        people = int(request.form.get('people'))
        budget = float(request.form.get('budget'))
        
        # Store search parameters in session
        request.session['search_params'] = {
            'destination': destination,
            'days': days,
            'people': people,
            'budget': budget
        }
        
        return redirect(url_for('main.recommendations'))
    
    return render_template('search.html', destinations=INDIAN_DESTINATIONS.keys())

@main_bp.route('/recommendations')
@login_required
def recommendations():
    params = request.session.get('search_params', {})
    if not params:
        return redirect(url_for('main.search'))
    
    destination = params['destination']
    days = params['days']
    people = params['people']
    budget = params['budget']
    
    # Get recommendations for the destination
    dest_data = INDIAN_DESTINATIONS.get(destination, {})
    
    # Calculate per person budget
    per_person_budget = budget / people if people > 0 else budget
    
    # Filter hotels by budget
    recommended_hotels = [
        hotel for hotel in dest_data.get('hotels', [])
        if float(hotel['price_range'].split('-')[0].replace('₹','').replace(',','')) <= per_person_budget
    ]
    
    return render_template('recommendations.html',
                         destination=destination,
                         days=days,
                         people=people,
                         budget=budget,
                         hotels=recommended_hotels,
                         attractions=dest_data.get('attractions', []))

@main_bp.route('/create_itinerary', methods=['POST'])
@login_required
def create_itinerary():
    params = request.session.get('search_params', {})
    if not params:
        return redirect(url_for('main.search'))
    
    selected_hotel = request.form.get('hotel')
    selected_attractions = request.form.getlist('attractions')
    
    # Create new itinerary
    itinerary = Itinerary(
        destination=params['destination'],
        days=params['days'],
        people=params['people'],
        budget=params['budget'],
        user_id=current_user.id
    )
    db.session.add(itinerary)
    db.session.commit()
    
    # Add places to itinerary
    dest_data = INDIAN_DESTINATIONS.get(params['destination'], {})
    
    # Add selected hotel
    for hotel in dest_data.get('hotels', []):
        if hotel['name'] == selected_hotel:
            place = Place(
                name=hotel['name'],
                category='Hotel',
                rating=hotel['rating'],
                price_range=hotel['price_range'],
                itinerary_id=itinerary.id
            )
            db.session.add(place)
    
    # Add selected attractions
    for attraction in dest_data.get('attractions', []):
        if attraction['name'] in selected_attractions:
            place = Place(
                name=attraction['name'],
                category=attraction['category'],
                itinerary_id=itinerary.id
            )
            db.session.add(place)
    
    db.session.commit()
    
    return redirect(url_for('main.view_itinerary', itinerary_id=itinerary.id))

@main_bp.route('/itinerary/<int:itinerary_id>')
@login_required
def view_itinerary(itinerary_id):
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    if itinerary.user_id != current_user.id:
        flash('You do not have permission to view this itinerary', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('itinerary.html', itinerary=itinerary)

@main_bp.route('/share_itinerary/<int:itinerary_id>', methods=['POST'])
@login_required
def share_itinerary(itinerary_id):
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    if itinerary.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    email = request.form.get('email')
    # In a real app, you would send the email here
    # For now, we'll just return a success message
    return jsonify({
        'success': True,
        'message': f'Itinerary shared successfully with {email}'
    })
