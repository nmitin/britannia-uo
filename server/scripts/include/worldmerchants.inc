/////////////////////////////////////////////////////////////////////////////
//
// worldmerchants.inc - торговцы/банкиры из штатного nodes.xml.
//
// В ModernDistro торговцы создаются не спавн-регионами, а MerchantNode
// (0x1887A). Готовый набор узлов лежит в
// `pkg/systems/merchantnodes/backups/nodes.xml`; берём только Felucca
// (realm britannia), чтобы не тащить отсутствующие у нас фасеты.
//
/////////////////////////////////////////////////////////////////////////////

use uo;
use os;
use file;
use util;
use polsys;

var WM_XML          := ":merchantnodes:backups/nodes.xml";
var WM_REGISTRY     := "WorldMerchants.Serials";
var WM_CPROP        := "WorldMerchantNode";


function WMLoadRegistry()

	var registry := GetGlobalProperty( WM_REGISTRY );
	if( TypeOfInt( registry ) != OT_ARRAY )
		registry := {};
	endif
	return registry;
endfunction


function WMSaveRegistry( registry )

	SetGlobalProperty( WM_REGISTRY, registry );
	return registry;
endfunction


function WMRemove()

	var result := struct{ "Destroyed":=0, "Missing":=0 };
	foreach serial in WMLoadRegistry()
		var item := SystemFindObjectBySerial( serial );
		if( item && GetObjProperty( item, WM_CPROP ) )
			DestroyItem( item );
			result.Destroyed += 1;
		else
			result.Missing += 1;
		endif
	endforeach
	WMSaveRegistry( {} );
	return result;
endfunction


function WMCount()

	var count := 0;
	foreach serial in WMLoadRegistry()
		var item := SystemFindObjectBySerial( serial );
		if( item && GetObjProperty( item, WM_CPROP ) )
			count += 1;
		endif
	endforeach
	return count;
endfunction


function WMSeed()

	var result := struct{ "Created":=0, "Existing":=0, "Failed":=0,
	                      "Total":=0, "Message":="" };

	var xml := OpenXMLFile( WM_XML );
	if( xml.errortext )
		result.Message := "не удалось открыть " + WM_XML + ": " + xml.errortext;
		return result;
	endif

	var facet := xml["Facets"]["Felucca"];
	if( facet.errortext )
		result.Message := "в nodes.xml нет Felucca";
		return result;
	endif

	var nodes := facet["MerchantNodes"];
	if( nodes.errortext )
		result.Message := "в Felucca нет MerchantNodes";
		return result;
	endif

	var new_registry := {};
	foreach node in nodes
		var realm := node.attributes["Realm"];
		var x := CInt( node.attributes["X"] );
		var y := CInt( node.attributes["Y"] );
		var z := CInt( node.attributes["Z"] );
		if( !realm )
			realm := "britannia";
		endif

		var existing := 0;
		foreach item in ListItemsAtLocation( x, y, z, realm )
			if( GetObjProperty( item, WM_CPROP ) )
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

			var cprops := Unpack( node.attributes["CProps"] );
			if( cprops.errortext )
				result.Failed += 1;
				Print( "WorldMerchants: не удалось распаковать CProps узла " + x + "," + y );
			else
				foreach prop in cprops
					desc.CProps.Insert( prop[1], prop[2] );
				endforeach
				desc.CProps.Insert( "Status", "on" );

				var item := CreateItemAtLocation( x, y, z, desc, 1, realm );
				if( item.errortext )
					result.Failed += 1;
					Print( "WorldMerchants: не удалось создать узел " + x + "," + y +
					       ": " + item.errortext );
				else
					SetObjProperty( item, WM_CPROP, 1 );
					item.decayAt := 0;
					new_registry.append( item.serial );
					result.Created += 1;
				endif
			endif
		endif

		result.Total += 1;
		if( result.Total % 25 == 0 )
			sleepms( 1 );
		endif
	endforeach

	WMSaveRegistry( new_registry );
	return result;
endfunction
