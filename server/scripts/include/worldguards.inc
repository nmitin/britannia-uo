/////////////////////////////////////////////////////////////////////////////
//
// worldguards.inc - guard-посты Британии.
//
// Источник: NPC `:guards:townguard`/`:guards:warrior` из сейва World of Dream.
// В ModernDistro на их координатах создаётся GuardNode (0x1887B), который
// сам спавнит `townguard` и обрабатывает вызовы стражи.
//
/////////////////////////////////////////////////////////////////////////////

use uo;
use os;
use cfgfile;

var WG_CFG          := "worldguards";
var WG_REGISTRY     := "WorldGuards.Serials";
var WG_VERSION_PROP := "WorldGuards.Version";
var WG_VERSION      := 1;
var WG_CPROP        := "WorldGuard";


function WGLoadRegistry()

	var registry := GetGlobalProperty( WG_REGISTRY );
	if( TypeOfInt( registry ) != OT_ARRAY )
		registry := {};
	endif
	return registry;
endfunction


function WGSaveRegistry( registry )

	SetGlobalProperty( WG_REGISTRY, registry );
	return registry;
endfunction


function WGRemove()

	var result := struct{ "Destroyed":=0, "Missing":=0 };
	foreach serial in WGLoadRegistry()
		var item := SystemFindObjectBySerial( serial );
		if( item && GetObjProperty( item, WG_CPROP ) )
			DestroyItem( item );
			result.Destroyed += 1;
		else
			result.Missing += 1;
		endif
	endforeach
	WGSaveRegistry( {} );
	return result;
endfunction


function WGCount()

	var count := 0;
	foreach serial in WGLoadRegistry()
		var item := SystemFindObjectBySerial( serial );
		if( item && GetObjProperty( item, WG_CPROP ) )
			count += 1;
		endif
	endforeach
	return count;
endfunction


function WGPlace()

	var result := struct{ "Created":=0, "Existing":=0, "Failed":=0,
	                      "Total":=0, "Message":="" };

	var cfg := ReadConfigFile( WG_CFG );
	if( cfg.errortext )
		result.Message := "не удалось прочитать " + WG_CFG + ": " + cfg.errortext;
		return result;
	endif

	var installed := CInt( GetGlobalProperty( WG_VERSION_PROP ) );
	if( installed < WG_VERSION )
		var removed := WGRemove();
		Print( "WorldGuards: обновление набора, удалено старых: " + removed.Destroyed );
	endif

	var new_registry := {};
	var keys := GetConfigIntKeys( cfg );
	var i := 0;

	foreach key in keys
		var elem := FindConfigElem( cfg, key );
		var x := CInt( elem.X );
		var y := CInt( elem.Y );
		var z := CInt( elem.Z );
		var realm := elem.Realm;
		if( !realm )
			realm := "britannia";
		endif

		var existing := 0;
		foreach item in ListItemsAtLocation( x, y, z, realm )
			if( GetObjProperty( item, WG_CPROP ) )
				existing := item;
				break;
			endif
		endforeach

		if( existing )
			SetObjProperty( existing, "Type", "townguard" );
			SetObjProperty( existing, "Amount", 1 );
			existing.movable := 0;
			if( existing.decayAt )
				existing.decayAt := 0;
			endif
			new_registry.append( existing.serial );
			result.Existing += 1;
		else
			var item := CreateItemAtLocation( x, y, z, "GuardNode", 1, realm );
			if( item.errortext )
				result.Failed += 1;
				Print( "WorldGuards: не удалось создать узел " + x + "," + y + "," + z +
				       ": " + item.errortext );
			else
				SetObjProperty( item, WG_CPROP, 1 );
				SetObjProperty( item, "Type", "townguard" );
				SetObjProperty( item, "Amount", 1 );
				item.movable := 0;
				item.decayAt := 0;
				new_registry.append( item.serial );
				result.Created += 1;
			endif
		endif

		result.Total += 1;
		i += 1;
		if( i % 50 == 0 )
			sleepms( 1 );
		endif
	endforeach

	WGSaveRegistry( new_registry );
	SetGlobalProperty( WG_VERSION_PROP, WG_VERSION );
	return result;
endfunction
