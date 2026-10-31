/////////////////////////////////////////////////////////////////////////////
//
// worldteleporters.inc - dungeon-телепорты Британии.
//
// Источник: сейв World of Dream (ObjType 0x6203). В ModernDistro тот же
// предмет называется `dungtele` (0x16203) и использует WalkOnScript makeDTele.
// Конфиг: `tools/import_teleporters.py` -> `config/worldteleporters.cfg`.
//
/////////////////////////////////////////////////////////////////////////////

use uo;
use os;
use cfgfile;

var WORLDTP_CFG          := "worldteleporters";
var WORLDTP_REGISTRY     := "WorldTeleporters.Serials";
var WORLDTP_VERSION_PROP := "WorldTeleporters.Version";
var WORLDTP_VERSION      := 1;
var WORLDTP_CPROP        := "WorldTeleporter";


function WorldTPLoadRegistry()

	var registry := GetGlobalProperty( WORLDTP_REGISTRY );
	if( TypeOfInt( registry ) != OT_ARRAY )
		registry := {};
	endif
	return registry;
endfunction


function WorldTPSaveRegistry( registry )

	SetGlobalProperty( WORLDTP_REGISTRY, registry );
	return registry;
endfunction


function WorldTPRemove()

	var result := struct{ "Destroyed":=0, "Missing":=0 };
	foreach serial in WorldTPLoadRegistry()
		var item := SystemFindObjectBySerial( serial );
		if( item && GetObjProperty( item, WORLDTP_CPROP ) )
			DestroyItem( item );
			result.Destroyed += 1;
		else
			result.Missing += 1;
		endif
	endforeach
	WorldTPSaveRegistry( {} );
	return result;
endfunction


function WorldTPCount()

	var count := 0;
	foreach serial in WorldTPLoadRegistry()
		var item := SystemFindObjectBySerial( serial );
		if( item && GetObjProperty( item, WORLDTP_CPROP ) )
			count += 1;
		endif
	endforeach
	return count;
endfunction


function WorldTPPlace()

	var result := struct{ "Created":=0, "Existing":=0, "Failed":=0,
	                      "Total":=0, "Message":="" };

	var cfg := ReadConfigFile( WORLDTP_CFG );
	if( cfg.errortext )
		result.Message := "не удалось прочитать " + WORLDTP_CFG + ": " + cfg.errortext;
		return result;
	endif

	var installed := CInt( GetGlobalProperty( WORLDTP_VERSION_PROP ) );
	if( installed < WORLDTP_VERSION )
		var removed := WorldTPRemove();
		Print( "WorldTeleporters: обновление набора, удалено старых: " + removed.Destroyed );
	endif

	var new_registry := {};
	var keys := GetConfigIntKeys( cfg );
	var i := 0;

	foreach key in keys
		var elem := FindConfigElem( cfg, key );
		var x := CInt( elem.X );
		var y := CInt( elem.Y );
		var z := CInt( elem.Z );
		var destx := CInt( elem.DestX );
		var desty := CInt( elem.DestY );
		var destz := CInt( elem.DestZ );
		var realm := elem.Realm;
		var destrealm := elem.DestRealm;

		if( !realm )
			realm := "britannia";
		endif
		if( !destrealm )
			destrealm := "britannia";
		endif

		var existing := 0;
		foreach item in ListItemsAtLocation( x, y, z, realm )
			if( GetObjProperty( item, WORLDTP_CPROP ) )
				existing := item;
				break;
			endif
		endforeach

		if( existing )
			SetObjProperty( existing, "DestX", destx );
			SetObjProperty( existing, "DestY", desty );
			SetObjProperty( existing, "DestZ", destz );
			SetObjProperty( existing, "DestRealm", destrealm );
			existing.movable := 0;
			if( existing.decayAt )
				existing.decayAt := 0;
			endif
			new_registry.append( existing.serial );
			result.Existing += 1;
		else
			var item := CreateItemAtLocation( x, y, z, "dungtele", 1, realm );
			if( item.errortext )
				result.Failed += 1;
				Print( "WorldTeleporters: не удалось создать " + x + "," + y + "," + z +
				       ": " + item.errortext );
			else
				SetObjProperty( item, "DestX", destx );
				SetObjProperty( item, "DestY", desty );
				SetObjProperty( item, "DestZ", destz );
				SetObjProperty( item, "DestRealm", destrealm );
				SetObjProperty( item, WORLDTP_CPROP, 1 );
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

	WorldTPSaveRegistry( new_registry );
	SetGlobalProperty( WORLDTP_VERSION_PROP, WORLDTP_VERSION );
	return result;
endfunction
