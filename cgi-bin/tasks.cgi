#!/usr/bin/perl
use strict;
use warnings;
use CGI qw(:standard);
use DBI;
use JSON;

# Configure the database connection
my $dsn = "DBI:mysql:database=poll_system;host=localhost";
my $db_user = 'root';
my $db_password = '';

# Function to get the database connection
sub get_db_connection {
    my $dbh = DBI->connect($dsn, $db_user, $db_password, { RaiseError => 1, AutoCommit => 1, mysql_enable_utf8 => 1 });
    return $dbh;
}

# Home route
sub home {
    print header('application/json');
    print encode_json({ message => 'Poll System API' });
}

# List polls
sub list_polls {
    my $dbh = get_db_connection();
    my $sth = $dbh->prepare('SELECT * FROM polls');
    $sth->execute();
    my $results = $sth->fetchall_arrayref({});
    $dbh->disconnect();
    print header('application/json');
    print encode_json($results);
}

# Get user details v2
sub get_user_v2 {
    my $poll_id = param('id');
    my $dbh = get_db_connection();
    my $sth = $dbh->prepare('SELECT * FROM users WHERE id = ?');
    $sth->execute($poll_id);
    my $poll_results = $sth->fetchrow_hashref();
    if (!$poll_results) {
        print header('application/json', '404 Not Found');
        print encode_json({ error => 'Poll not found' });
        return;
    }

    $sth = $dbh->prepare('SELECT * FROM users WHERE id = ?');
    $sth->execute($poll_id);
    my $option_results = $sth->fetchall_arrayref({});
    my $poll = {
        username => $poll_results->{username},
        password => $poll_results->{password}
    };
    $dbh->disconnect();
    print header('application/json');
    print encode_json($poll);
}

# Get list of users
sub get_users {
    my $dbh = get_db_connection();
    my $sth = $dbh->prepare('SELECT * FROM users');
    $sth->execute();
    my $results = $sth->fetchall_arrayref({});
    $dbh->disconnect();
    print header('application/json');
    print encode_json($results);
}

# Create new poll
sub create_poll {
    my $query = new CGI;
    my $data = decode_json($query->param('POSTDATA'));

    my $question = $data->{question};
    my $options = $data->{options};
    my $created_by = $data->{id};

    if (!$question || !$options || !$created_by) {
        print header('application/json', '400 Bad Request');
        print encode_json({ error => 'Missing required fields' });
        return;
    }

    my $dbh = get_db_connection();
    my $sth = $dbh->prepare('INSERT INTO polls (question, created_by) VALUES (?, ?)');
    $sth->execute($question, $created_by);
    my $poll_id = $dbh->{mysql_insertid};

    $sth = $dbh->prepare('INSERT INTO options (poll_id, option_text) VALUES (?, ?)');
    foreach my $option (@$options) {
        $sth->execute($poll_id, $option);
    }
    
    $dbh->disconnect();
    print header('application/json');
    print encode_json({ status => 'success' });
}

# Get poll details
sub get_poll {
    my $poll_id = param('id');
    my $dbh = get_db_connection();
    my $sth = $dbh->prepare('SELECT * FROM polls WHERE id = ?');
    $sth->execute($poll_id);
    my $poll_results = $sth->fetchrow_hashref();
    if (!$poll_results) {
        print header('application/json', '404 Not Found');
        print encode_json({ error => 'Poll not found' });
        return;
    }

    $sth = $dbh->prepare('SELECT * FROM options WHERE poll_id = ?');
    $sth->execute($poll_id);
    my $option_results = $sth->fetchall_arrayref({});
    my $poll = {
        question => $poll_results->{question},
        options => $option_results
    };
    $dbh->disconnect();
    print header('application/json');
    print encode_json($poll);
}

# Get user details
sub get_user {
    my $poll_id = param('id');
    my $dbh = get_db_connection();
    my $sth = $dbh->prepare('SELECT * FROM users WHERE id = ?');
    $sth->execute($poll_id);
    my $user_results = $sth->fetchrow_hashref();
    if (!$user_results) {
        print header('application/json', '404 Not Found');
        print encode_json({ error => 'User not found' });
        return;
    }

    $dbh->disconnect();
    print header('application/json');
    print encode_json($user_results);
}

# Vote in poll
sub vote {
    my $query = new CGI;
    my $data = decode_json($query->param('POSTDATA'));

    my $poll_id = $data->{poll_id};
    my $option_id = $data->{option_id};
    my $user_id = $data->{id};

    my $dbh = get_db_connection();
    my $sth = $dbh->prepare('INSERT INTO votes (poll_id, option_id, user_id) VALUES (?, ?, ?)');
    eval {
        $sth->execute($poll_id, $option_id, $user_id);
    };
    if ($@) {
        print header('application/json', '500 Internal Server Error');
        print encode_json({ error => $@ });
        return;
    }
    
    $dbh->disconnect();
    print header('application/json');
    print encode_json({ status => 'success' });
}

# Get poll results
sub get_results {
    my $poll_id = param('id');
    my $dbh = get_db_connection();
    my $sth = $dbh->prepare('SELECT * FROM polls WHERE id = ?');
    $sth->execute($poll_id);
    my $poll_results = $sth->fetchrow_hashref();
    if (!$poll_results) {
        print header('application/json', '404 Not Found');
        print encode_json({ error => 'Poll not found' });
        return;
    }

    $sth = $dbh->prepare('SELECT options.option_text, COUNT(votes.id) AS votes FROM options LEFT JOIN votes ON options.id = votes.option_id WHERE options.poll_id = ? GROUP BY options.id');
    $sth->execute($poll_id);
    my $result = $sth->fetchall_arrayref({});
    my $results = {
        question => $poll_results->{question},
        results => $result
    };
    $dbh->disconnect();
    print header('application/json');
    print encode_json($results);
}

# Define routes
my %routes = (
    '/' => \&home,
    '/list_polls' => \&list_polls,
    '/v2/user' => \&get_user_v2,
    '/v1/user' => \&get_users,
    '/create_poll' => \&create_poll,
    '/get_poll' => \&get_poll,
    '/user' => \&get_user,
    '/vote' => \&vote,
    '/get_results' => \&get_results
);

# Routing
my $path = url(-absolute => 1);
if (exists $routes{$path}) {
    $routes{$path}->();
} else {
    print header('application/json', '404 Not Found');
    print encode_json({ error => 'Route not found' });
}
