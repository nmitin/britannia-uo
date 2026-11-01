/////////////////////////////////////////////////////////////////////////////
//
// worldspecials.inc - особые NPC: лекари и стейблмастеры из World of Dream.
//
// Координаты в config/worldspecials.cfg (tools/import_specials.py). На каждой
// точке создаётся MerchantNode с предзаполненным DeathList: control-скрипт
// при старте форс-респавнит NPC, сотрёт DeathList и заполнит MerchantInfo —
// тот же механизм, что у штатных узлов из nodes.xml.
//
// Бродячие лекари (180 точек) засеиваются один раз в datafile
// :npcs:specialNPCs — дальше их поддерживает verifySpecialNPCs на каждом
// сейве. `.seednodes` не используем: он засеял бы дубли всех merchant-узлов.
//
/////////////////////////////////////////////////////////////////////////////

use uo;
use os;
use polsys;
use cfgfile;
use datafile;

var WS_CFG           := "worldspecials";
var WS_REGISTRY      := "WorldSpecials.Serials";
var WS_VERSION_PROP  := "WorldSpecials.Version";
var WS_VERSION       := 3;
var WS_CPROP         := "WorldSpecialNode";
var WS_HEALERS_SEEDED := "WorldSpecials.HealersSeeded";
var WS_HEALERS_CFG   := ":npcs:specialNPCs";
var WS_HEALERS_FACET := "britannia";
var WS_HEALERS_REALM := "britannia";


function WSLoadRegistry()

	var registry := GetGlobalProperty( WS_REGISTRY );
	if( TypeOfInt( registry ) != OT_ARRAY )
		registry := {};
	endif
	return registry;
endfunction


function WSSaveRegistry( registry )

	SetGlobalProperty( WS_REGISTRY, registry );
	return registry;
endfunction


function WSRemove()

	var result := struct{ "Destroyed":=0, "Missing":=0 };
	foreach serial in WSLoadRegistry()
		var item := SystemFindObjectBySerial( serial );
		if( item && GetObjProperty( item, WS_CPROP ) )
			DestroyItem( item );
			result.Destroyed += 1;
		else
			result.Missing += 1;
		endif
	endforeach
	WSSaveRegistry( {} );
	return result;
endfunction


function WSCount()

	var count := 0;
	foreach serial in WSLoadRegistry()
		var item := SystemFindObjectBySerial( serial );
		if( item && GetObjProperty( item, WS_CPROP ) )
			count += 1;
		endif
	endforeach
	return count;
endfunction


// Сборка MerchantInfo-записи для узла: как struct Info в nodes.xml.
function WSBuildInfo( template, x, y, z, realm, name, gender )

	return Struct{
		"Anchor" := Struct{ "X":=x, "Y":=y, "Z":=z, "Realm":=realm },
		"Enabled" := 1,
		"Info" := Struct{
			"Gender" := gender,
			"Name" := name,
			"RandomizeSkinHue" := 1,
			"RandomizeSpeechHue" := 1
			},
		"Template" := template
		};
endfunction


function WSPlace()

	var result := struct{ "Created":=0, "Existing":=0, "Failed":=0,
	                      "Total":=0, "Message":="" };

	var cfg := ReadConfigFile( WS_CFG );
	if( cfg.errortext )
		result.Message := "не удалось прочитать " + WS_CFG + ": " + cfg.errortext;
		return result;
	endif

	var installed := CInt( GetGlobalProperty( WS_VERSION_PROP ) );
	if( installed < WS_VERSION )
		var removed := WSRemove();
		Print( "WorldSpecials: обновление набора, удалено старых узлов: " + removed.Destroyed );
	endif

	var new_registry := {};
	var keys := GetConfigIntKeys( cfg );
	var i := 0;

	foreach key in keys
		var elem := FindConfigElem( cfg, key );
		var template := elem.Type;
		var x := CInt( elem.X );
		var y := CInt( elem.Y );
		var z := CInt( elem.Z );
		var realm := elem.Realm;
		if( !realm )
			realm := "britannia";
		endif

		var existing := 0;
		foreach item in ListItemsAtLocation( x, y, z, realm )
			if( GetObjProperty( item, WS_CPROP ) )
				existing := item;
				break;
			endif
		endforeach

		if( existing )
			new_registry.append( existing.serial );
			result.Existing += 1;
		else
			var desc := GetItemDescriptor( GetObjtypeByName( "MerchantNode" ) );
			desc.Color := 0;
			desc.Invisible := 1;
			desc.Movable := 0;

			// DeathList с Time=0 заставляет control-скрипт при старте
			// форс-респавнить NPC (respawnAllMerchants, force=TRUE).
			desc.CProps.Insert( "DeathList", Dictionary{ 1 -> Struct{
				"Info" := WSBuildInfo( template, x, y, z, realm,
				                       elem.Name, CInt( elem.Gender) ),
				"Time" := 0
				} } );
			desc.CProps.Insert( "MerchantInfo", Dictionary );
			desc.CProps.Insert( "Range", 15 );
			desc.CProps.Insert( "Status", "on" );

			var item := CreateItemAtLocation( x, y, z, desc, 1, realm );
			if( item.errortext )
				result.Failed += 1;
				Print( "WorldSpecials: не удалось создать узел " + x + "," + y +
				       ": " + item.errortext );
			else
				SetObjProperty( item, WS_CPROP, 1 );
				item.decayAt := 0;
				new_registry.append( item.serial );
				result.Created += 1;
			endif
		endif

		result.Total += 1;
		i += 1;
		if( i % 25 == 0 )
			sleepms( 1 );
		endif
	endforeach

	WSSaveRegistry( new_registry );
	SetGlobalProperty( WS_VERSION_PROP, WS_VERSION );
	return result;
endfunction


function WSSeedHealers()

	var result := struct{ "Created":=0, "Existing":=0, "Failed":=0,
	                      "Total":=0, "Message":="" };

	if( GetGlobalProperty( WS_HEALERS_SEEDED ) )
		result.Existing := WSCountHealers();
		return result;
	endif

	var cfg := ReadConfigFile( WS_HEALERS_CFG );
	if( cfg.errortext )
		result.Message := "не удалось прочитать " + WS_HEALERS_CFG + ": " + cfg.errortext;
		return result;
	endif

	var facet := FindConfigElem( cfg, WS_HEALERS_FACET );
	if( facet.errortext )
		result.Message := "в " + WS_HEALERS_CFG + " нет фасета " + WS_HEALERS_FACET;
		return result;
	endif

	var locations := GetConfigStringArray( facet, "Location" );
	var df := CreateDataFile( WS_HEALERS_CFG, DF_KEYTYPE_INTEGER );
	if( df.errortext )
		result.Message := "не удалось создать datafile " + WS_HEALERS_CFG + ": " + df.errortext;
		return result;
	endif

	var overrides := struct;
	foreach location in locations
		var parts := SplitWords( location );
		var template := parts[1];
		var x := CInt( parts[2] );
		var y := CInt( parts[3] );
		var z := CInt( parts[4] );

		var npc := CreateNpcFromTemplate( template, x, y, z, overrides, WS_HEALERS_REALM );
		if( !npc )
			result.Failed += 1;
			Print( "WorldSpecials: не создать " + template + " в " + x + "," + y + "," + z +
			       ": " + npc.errortext );
		else
			var elem := df.CreateElement( npc.serial );
			elem.SetProp( "template", template );
			elem.SetProp( "x", x );
			elem.SetProp( "y", y );
			elem.SetProp( "z", z );
			elem.SetProp( "facet", WS_HEALERS_REALM );
			result.Created += 1;
		endif
		result.Total += 1;
		if( result.Total % 25 == 0 )
			sleepms( 1 );
		endif
	endforeach

	SetGlobalProperty( WS_HEALERS_SEEDED, 1 );

	// Пометить фасет засеянным, чтобы .seednodes его больше не предлагал.
	var seeded := GetGlobalProperty( "MerchantSeededFacets" );
	if( TypeOfInt( seeded ) != OT_ARRAY )
		seeded := {};
	endif
	if( !( WS_HEALERS_FACET in seeded ) )
		seeded.append( WS_HEALERS_FACET );
		SetGlobalProperty( "MerchantSeededFacets", seeded );
	endif

	return result;
endfunction


function WSCountHealers()

	var df := OpenDataFile( WS_HEALERS_CFG );
	if( df.errortext )
		return 0;
	endif
	return df.Keys().Size();
endfunction
