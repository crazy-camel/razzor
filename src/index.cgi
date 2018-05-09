#!/usr/bin/perl

use utf8;
use strict;
use warnings qw/all/;

use Env;
use CGI::Fast;
use JSON::XS;
use Template::Mustache;

use Path::Tiny qw/path/;
use Config::Tiny;
use Data::Dump;
use Scalar::Util;

# ----------------------------------------------------------------------
# | Initialization                                                     |
# ----------------------------------------------------------------------
my $base = path( $0 )->parent();
my $config = ( $base->child('index.ini')->exists() )
				? Config::Tiny->new( $base->child('index.ini')->stringify ): {};

# ----------------------------------------------------------------------
# | Fast::CGI Response Loop                                            |
# ----------------------------------------------------------------------
while (my $q = CGI::Fast->new() )
{
	#print $q->header( -status => 200, -charset => 'UTF-8' );

	my ( $route, @filters ) = route( $q );

	if ( $route eq '404' )
	{
		print _404( $q );
		next;
	}

	my $data = model( $q, $route, @filters );

	my $view = Template::Mustache->new(
    	template_path   => $route->child('view.mustache')->stringify,
    	partials_path	=> $base->child('partials')->stringify
	);
	# TODO:
	# add cookie into this mix
	print $q->header( -status => 200, -charset => 'UTF-8' );
	print $view->render( $data );
}


# ----------------------------------------------------------------------
# | Helper Functions		                                           |
# ----------------------------------------------------------------------

sub route
{
	my ( $query ) = @_;

	# lets get the path and try to resolve it
	my $path = ( length( $query->request_uri ) > 1 ) ? $query->request_uri : '/welcome';
	
	my @fragments = grep { $_ ne '' } split /\//, $path;

	my ( @resource, @parameters ) = ( undef, undef );

	for (my $i = $#fragments; $i > -1; $i--)
	{
    	my @path = @fragments[0..$i];

    	if ( $base->child( @path, "view.mustache" )->exists() )
		{
			@resource = @path;
			last;
		}                   
    	
    	push @parameters, $fragments[$i];
    }
	
	# lets return a 404 if we do not have anything
	return ( '404', undef ) unless ( $resource[0] );

	if ( @parameters )
	{
		@parameters = reverse @parameters;
		push @parameters, '*' if ( @parameters % 2 != 0 );
	}

	return ( $base->child( @resource ), @parameters );
}

sub model
{
	my ( $query, $route, @filters ) = ( @_ );

	my $data = ( scalar $query->param ) ? $query->Vars : {};

	if ( $route->child('data.json')->exists() )
	{
		my $json = decode_json $route->child('data.json')->slurp_utf8;

		$data = { %$data , %$json };
	}

	return ( @filters ) ? filter( $data, @filters ) : $data;

}

sub _404
{
	return join( "",
		$_[0]->header( -status => 404, -charset => 'UTF-8' ),
		$base->child( '404.html' )->slurp_utf8()
		);
}

sub filter
{
	my ( $data, @filters ) = @_;
	while ( my ( $key, $value ) = splice( @filters, 0, 2 ) )
	{
	 	
	 	if ( Scalar::Util::looks_like_number( $key ) &&  $data->{'meta'}->{'pagination'} )
	 	{
	 	 	my @array = @{ $data->{'data'} };
	 	 	my ( $start, $end ) = ( $key, $key + $data->{'meta'}->{'pagination'} );
	 	 	$data->{'data'} = ( $end < scalar (@array)  ) ? [ splice( @array, $start, $end) ] : [ splice( @array, $start) ];
	 	 	next;
	 	}

	 	$data->{'data'} = (  $value ne '*'  ) 
	 		? [ grep { lc( $_->{ $key } ) eq $value } @{ $data->{'data'} } ]
	 		: [ grep { exists $_->{ $key }  } @{ $data->{'data'} }  ];
	}

	return $data;
}