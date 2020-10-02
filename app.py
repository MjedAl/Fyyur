#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, jsonify, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from sqlalchemy import desc
from models import *

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)

db.create_all()

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  """
    This method will be called when the client connects to the default route of the website
    it will then call the latest 10 added artists and venues from the database and pass it to the
    home.html to render and return the data with the html for the client
  """
  artists = Artist.query.order_by(Artist.id.desc()).limit(10)
  venues = Venue.query.order_by(Venue.id.desc()).limit(10)
  return render_template('pages/home.html', artists = artists, venues = venues)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  """
    This method will be called when the client connects to the venues page
    it will then first get all the unique area names (city, state) in order to
    categorize all the venues based on these areas
    return: html page with venues categorized based on city and state
  """
  areas = Venue.query.distinct(Venue.city, Venue.state)
  data = []
  for area in areas:
    uniqueArea = {
      "city": area.city,
      "state": area.state,
      "venues": []
    }
    # get all the venues in this unique area and add it
    venues = Venue.query.filter_by(city=area.city, state=area.state)
    for venue in venues:
      uniqueArea["venues"].append({
        "id": venue.id,
        "name": venue.name
      })
    data.append(uniqueArea)

  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  """
    Search for a venue method
    Called when a client wants to search for a specific venue
  ---
    parameters:
      - name: search_term
        in: forum
        type: string
        required: true
        description: the search term
    return:
      template:
        description: with the data related to the search term
  """
  search_term=request.form.get('search_term', '')
  venues = Venue.query.filter(Venue.name.ilike('%'+search_term+'%')).all()

  response={
    "count": 0,
    "data": []
  }
  currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  for venue in venues:
    response["count"] = response["count"] + 1
    response["data"].append({
    "id": venue.id,
    "name": venue.name,
    "num_upcoming_shows": Venue.query.filter_by(id = venue.id).join(Show, Show.venue_id == Venue.id).filter(Show.start_time > currentTime).count()
    })

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  """
    Show a venue page
    ---
    parameters:
      - name: venue_id
        in: path
        type: int
        required: true
        description: the id for the venue
    return:
      template:
        description: a web page for the required venue with all of it's information
  """
  venue=Venue.query.get(venue_id)
  if not venue:
    return render_template('errors/404.html')
  data={
      "id": venue.id,
      "name": venue.name,
      "genres": venue.genres.replace('{',' ').replace('}',' ').split(','),
      "address": venue.address,
      "city": venue.city,
      "state": venue.state,
      "phone": venue.phone,
      "website": venue.website,
      "facebook_link": venue.facebook_link,
      "seeking_talent": venue.seeking_talent,
      "seeking_description": venue.seeking_description,
      "image_link": venue.image_link,
      "past_shows": [],
      "upcoming_shows": [],
      "past_shows_count": 0,
      "upcoming_shows_count": 0,
    }
  # check for shows related to this venue
  Shows = Show.query.filter_by(venue_id=venue.id)
  for show in Shows:
      artist = Artist.query.filter_by(id=show.artist_id).first()
      # check if show is upcoming or past
      currentTime = datetime.now()
      showTime = datetime.strptime(show.start_time, '%Y-%m-%d %H:%M:%S')
        
      if currentTime>showTime:
        data['past_shows'].append({
          "artist_id": artist.id,
          "artist_name": artist.name,
          "artist_image_link": artist.image_link,
          "start_time": show.start_time
        })
        data['past_shows_count']=data['past_shows_count']+1
      else:
        data['upcoming_shows'].append({
          "artist_id": artist.id,
          "artist_name": artist.name,
          "artist_image_link": artist.image_link,
          "start_time": show.start_time
        })
        data['upcoming_shows_count']=data['upcoming_shows_count']+1
  return render_template('pages/show_venue.html', venue=data)




#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  """
    this method will receive a POST request and a data from the form and it will
    create a new venue then add it to the database
    parameters:
      - name: request
        in: POST
        type: forum
        required: true
        description: all the new venue information
    return:
      a flash:
        description: a message whether the venue was added or the task failed.
  """
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    address = request.form['address']
    phone = request.form['phone']
    genres = request.form.getlist('genres')
    facebook_link = request.form['facebook_link']
    newVenue = Venue(name=name, city=city, state=state, address=address, phone=phone, genres=genres, facebook_link=facebook_link)
    db.session.add(newVenue)
    db.session.commit()
    # on successful db insert, flash success
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    venue = Venue.query.get(venue_id)
    db.session.delete(venue)
    db.session.commit()
    flash('Venue was successfully deleted!')
    return jsonify({'success': True}) 
  except:
    db.session.rollback()
    flash('An error occurred. while deleting the.')
  finally:
    db.session.close()
  return jsonify({'success': False})

#  ----------------------------------------------------------------
#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  return render_template('pages/artists.html', artists=Artist.query.all())

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term=request.form.get('search_term', '')
  artists = Artist.query.filter(Artist.name.ilike('%'+search_term+'%')).all()
  
  response={
    "count": 0,
    "data": []
  }

  currentTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  for artist in artists:
    response["count"] = response["count"] + 1
    response["data"].append({
    "id": artist.id,
    "name": artist.name,
    "num_upcoming_shows": Artist.query.filter_by(id = artist.id).join(Show, Show.artist_id == artist.id).filter(Show.start_time > currentTime).count()
    })

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  """
    Show an artist page
    ---
    parameters:
      - name: artist_id
        in: path
        type: int
        required: true
        description: the id for the artist
    return:
      template:
        description: a web page for the required artist with all of the information
  """
  artist=Artist.query.get(artist_id)

  data={
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres.replace('{',' ').replace('}',' ').split(','),
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": [],
    "upcoming_shows": [],
    "past_shows_count": 0,
    "upcoming_shows_count": 0,
  }
  # check for shows related to this artist
  Shows = Show.query.filter_by(artist_id=artist.id)
  for show in Shows:
      venue = Venue.query.filter_by(id=show.venue_id).first()
      # check if show is upcoming or past
      currentTime = datetime.now()
      showTime = datetime.strptime(show.start_time, '%Y-%m-%d %H:%M:%S')
      
      if currentTime>showTime:
        data['past_shows'].append({
          "venue_id": venue.id,
          "venue_name": venue.name,
          "venue_image_link": venue.image_link,
          "start_time": show.start_time
        })
        data['past_shows_count']=data['past_shows_count']+1
      else:
        data['upcoming_shows'].append({
          "venue_id": venue.id,
          "venue_name": venue.name,
          "venue_image_link": venue.image_link,
          "start_time": show.start_time
        })
        data['upcoming_shows_count']=data['upcoming_shows_count']+1


  return render_template('pages/show_artist.html', artist=data)

#  ----------------------------------------------------------------
#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  return render_template('forms/edit_artist.html', form=form, artist=Artist.query.filter_by(id=artist_id).first())

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  try:
    artist = Artist.query.filter_by(id=artist_id).first()
    artist.name = request.form['name']
    artist.city = request.form['city']
    artist.state = request.form['state']
    artist.phone = request.form['phone']
    artist.genres = request.form.getlist('genres')
    artist.facebook_link = request.form['facebook_link']
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully edited!')
  except:
    db.session.rollback()
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be edited.')
  finally:
    db.session.close()
  # artist record with ID <artist_id> using the new attributes
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  return render_template('forms/edit_venue.html', form=form, venue=Venue.query.filter_by(id=venue_id).first())

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  try:
    venue = Venue.query.filter_by(id=venue_id).first()
    venue.name = request.form['name']
    venue.city = request.form['city']
    venue.state = request.form['state']
    venue.phone = request.form['phone']
    venue.genres = request.form.getlist('genres')
    venue.facebook_link = request.form['facebook_link']
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully edited!')
  except:
    db.session.rollback()
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be edited.')
  finally:
    db.session.close()
  # artist record with ID <artist_id> using the new attributes
  return redirect(url_for('show_venue', venue_id=venue_id))

#  ----------------------------------------------------------------
#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    phone = request.form['phone']
    genres = request.form.getlist('genres')
    facebook_link = request.form['facebook_link']
    newArtist = Artist(name=name, city=city, state=state, phone=phone, genres=genres, facebook_link=facebook_link)
    db.session.add(newArtist)
    db.session.commit()
    # on successful db insert, flash success
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()
    return render_template('pages/home.html')

#  ----------------------------------------------------------------
#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():  
  """
    this method will be called when the client visits the '/shows' route 
    it will get all the shows information from the database.
    return:
      template:
        description: the html page with the shows information in it
  """
  
  shows = Show.query.all()
  data = []
  for show in shows:
     venue = Venue.query.filter_by(id=show.venue_id).first()
     artist = Artist.query.filter_by(id=show.artist_id).first()
     data.append({
      "venue_id": show.venue_id,
      "venue_name": venue.name,
      "artist_id": artist.id,
      "artist_name": artist.name,
      "artist_image_link": artist.image_link,
      "start_time": show.start_time
    })
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    artistID = request.form['artist_id']
    venueID = request.form['venue_id']
    time = request.form['start_time']
    newShow = Show(artist_id=artistID, venue_id=venueID, start_time=time)
    db.session.add(newShow)
    db.session.commit()
    # on successful db insert, flash success
    flash('Show was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')
  finally:
    db.session.close()
  return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()
  

  





  

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
